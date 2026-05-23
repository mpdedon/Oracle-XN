"""
ORACLE-X/N — LLM Client
=========================
Unified LLM inference layer supporting Groq, OpenAI, and Ollama.
Handles retries, timeouts, JSON extraction, and provider switching.
"""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class LLMClient:
    """
    Provider-agnostic LLM client for ORACLE-X/N.
    Supports Groq (primary), OpenAI, and Ollama (local fallback).
    """

    def __init__(self, settings=None):
        if settings is None:
            from config import OracleSettings
            settings = OracleSettings()
        self.settings = settings
        self._client = None
        self._provider = settings.llm_provider
        self._init_client()

    def _init_client(self):
        """Lazily initialise the provider client."""
        if self._provider == "groq":
            try:
                from groq import Groq
                self._client = Groq(api_key=self.settings.groq_api_key)
                self._model = self.settings.groq_model
                logger.info(f"LLMClient: Groq initialised (model={self._model})")
            except ImportError:
                logger.warning("groq package not installed — falling back to openai")
                self._provider = "openai"
                self._init_client()

        elif self._provider == "openai":
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=self.settings.openai_api_key)
                self._model = self.settings.openai_model
                logger.info(f"LLMClient: OpenAI initialised (model={self._model})")
            except ImportError:
                logger.warning("openai package not installed — falling back to ollama")
                self._provider = "ollama"
                self._init_client()

        elif self._provider == "ollama":
            try:
                from openai import OpenAI
                self._client = OpenAI(
                    base_url=f"{self.settings.ollama_base_url}/v1",
                    api_key="ollama",  # Ollama doesn't need a real key
                )
                self._model = self.settings.ollama_model
                logger.info(f"LLMClient: Ollama initialised (model={self._model})")
            except ImportError:
                raise RuntimeError(
                    "No LLM provider available. Install groq, openai, or ollama."
                )

    def chat(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        """
        Send a chat completion request.
        Returns the raw text response string.
        """
        messages = [{"role": "system", "content": system_prompt}]

        if conversation_history:
            messages.extend(conversation_history)

        messages.append({"role": "user", "content": user_prompt})

        kwargs = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature or self.settings.llm_temperature,
            "max_tokens": max_tokens or self.settings.llm_max_tokens,
        }

        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self._client.chat.completions.create(**kwargs)
                content = response.choices[0].message.content
                return content or ""
            except Exception as e:
                error_str = str(e)
                if "rate_limit" in error_str.lower() and attempt < max_retries - 1:
                    wait = 2 ** attempt
                    logger.warning(f"Rate limit hit, retrying in {wait}s...")
                    time.sleep(wait)
                    continue
                logger.error(f"LLM call failed (attempt {attempt+1}): {e}")
                if attempt == max_retries - 1:
                    raise

        return ""

    def chat_stream(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ):
        """
        Streaming chat — yields text chunks as they arrive from the LLM.
        Use with Streamlit's st.write_stream() for real-time display.
        Falls back to non-streaming if provider doesn't support it.
        """
        messages = [{"role": "system", "content": system_prompt}]
        if conversation_history:
            messages.extend(conversation_history)
        messages.append({"role": "user", "content": user_prompt})

        kwargs = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature or self.settings.llm_temperature,
            "max_tokens": max_tokens or self.settings.llm_max_tokens,
            "stream": True,
        }

        try:
            stream = self._client.chat.completions.create(**kwargs)
            for chunk in stream:
                delta = chunk.choices[0].delta
                if delta and delta.content:
                    yield delta.content
        except Exception as e:
            logger.warning(f"Streaming failed ({e}), falling back to blocking call")
            # Fallback: yield full response at once
            result = self.chat(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                conversation_history=conversation_history,
            )
            yield result

    def chat_fast(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        """
        Blocking chat using the fast model (llama-3.1-8b-instant) for
        latency-sensitive paths: chat follow-ups, narrative identity.
        Falls back to the standard model if no fast model is configured.
        """
        fast_model = getattr(self.settings, "groq_fast_model", None)
        if self._provider == "groq" and fast_model:
            messages = [{"role": "system", "content": system_prompt}]
            if conversation_history:
                messages.extend(conversation_history)
            messages.append({"role": "user", "content": user_prompt})
            kwargs = {
                "model": fast_model,
                "messages": messages,
                "temperature": temperature or self.settings.llm_temperature,
                "max_tokens": max_tokens or self.settings.llm_max_tokens,
            }
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = self._client.chat.completions.create(**kwargs)
                    return response.choices[0].message.content or ""
                except Exception as e:
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)
                        continue
                    logger.warning(f"Fast model failed, falling back to standard: {e}")
                    break
        return self.chat(system_prompt, user_prompt, temperature, max_tokens, conversation_history)

    def chat_stream_fast(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ):
        """
        Streaming chat using the fast model (llama-3.1-8b-instant).
        Use for review text streaming, conversational follow-ups, and narrative identity.
        Falls back to standard chat_stream if fast model is unavailable.
        """
        fast_model = getattr(self.settings, "groq_fast_model", None)
        if self._provider != "groq" or not fast_model:
            yield from self.chat_stream(system_prompt, user_prompt, temperature, max_tokens, conversation_history)
            return

        messages = [{"role": "system", "content": system_prompt}]
        if conversation_history:
            messages.extend(conversation_history)
        messages.append({"role": "user", "content": user_prompt})

        kwargs = {
            "model": fast_model,
            "messages": messages,
            "temperature": temperature or self.settings.llm_temperature,
            "max_tokens": max_tokens or self.settings.llm_max_tokens,
            "stream": True,
        }
        try:
            stream = self._client.chat.completions.create(**kwargs)
            for chunk in stream:
                delta = chunk.choices[0].delta
                if delta and delta.content:
                    yield delta.content
        except Exception as e:
            logger.warning(f"Fast stream failed ({e}), falling back to standard model")
            yield from self.chat_stream(system_prompt, user_prompt, temperature, max_tokens, conversation_history)

    def chat_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Any:
        """
        Chat and parse the response as JSON.
        Handles messy LLM output with robust extraction.
        """
        temp = temperature or max(0.2, self.settings.llm_temperature - 0.3)
        raw = self.chat(system_prompt, user_prompt, temperature=temp, max_tokens=max_tokens)
        return self._extract_json(raw)

    def chat_json_fast(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Any:
        """
        chat_json using the fast model (llama-3.1-8b-instant).
        Use for LLM reranking and other structured-output paths that need speed.
        """
        temp = temperature or max(0.2, self.settings.llm_temperature - 0.3)
        raw = self.chat_fast(system_prompt, user_prompt, temperature=temp, max_tokens=max_tokens)
        return self._extract_json(raw)

    def _extract_json(self, text: str) -> Any:
        """
        Robustly extract JSON from LLM output.
        Handles markdown code fences, leading/trailing text, etc.
        """
        if not text:
            return {}

        # Try direct parse first
        text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Extract from markdown code fence
        fence_pattern = r"```(?:json)?\s*([\s\S]*?)\s*```"
        matches = re.findall(fence_pattern, text, re.IGNORECASE)
        for match in matches:
            try:
                return json.loads(match.strip())
            except json.JSONDecodeError:
                continue

        # Find the outermost JSON object or array
        for start_char, end_char in [('{', '}'), ('[', ']')]:
            start_idx = text.find(start_char)
            if start_idx == -1:
                continue
            # Walk to find matching close
            depth = 0
            in_string = False
            escape_next = False
            for i, ch in enumerate(text[start_idx:], start=start_idx):
                if escape_next:
                    escape_next = False
                    continue
                if ch == '\\' and in_string:
                    escape_next = True
                    continue
                if ch == '"' and not escape_next:
                    in_string = not in_string
                if not in_string:
                    if ch == start_char:
                        depth += 1
                    elif ch == end_char:
                        depth -= 1
                        if depth == 0:
                            try:
                                return json.loads(text[start_idx:i+1])
                            except json.JSONDecodeError:
                                break

        logger.warning(f"JSON extraction failed for text: {text[:200]}...")
        return {}

    def get_embedding(self, text: str) -> List[float]:
        """
        Generate a text embedding.
        Uses sentence-transformers (local) — not the LLM provider.
        """
        try:
            from sentence_transformers import SentenceTransformer
            if not hasattr(self, "_embedding_model"):
                self._embedding_model = SentenceTransformer(
                    self.settings.embedding_model
                )
            emb = self._embedding_model.encode(text, show_progress_bar=False)
            return emb.tolist()
        except ImportError:
            logger.error("sentence-transformers not installed")
            return [0.0] * self.settings.embedding_dimension

    def get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Batch embedding generation."""
        try:
            from sentence_transformers import SentenceTransformer
            if not hasattr(self, "_embedding_model"):
                self._embedding_model = SentenceTransformer(
                    self.settings.embedding_model
                )
            embeddings = self._embedding_model.encode(
                texts,
                batch_size=self.settings.embedding_batch_size,
                show_progress_bar=False,
            )
            return embeddings.tolist()
        except ImportError:
            return [[0.0] * self.settings.embedding_dimension] * len(texts)
