# ORACLE-X/N — Behavioural Cognitive Graph Agent

> **DSN × BCT LLM Agent Hackathon 2026 — Submission**
>
> *Task A: Psychologically authentic review & star-rating generation for unseen items*
> *Task B: Personalised contextual recommendations with agentic reasoning*

---

## What is ORACLE-X/N?

ORACLE-X/N (**O**ptimised **R**easoning **A**gent with **C**ognitive **L**earning &
**E**xcellence — e**X**tended **N**igerian) is a Behavioural Cognitive Graph Agent that
simulates the full psychological journey of a Nigerian digital consumer:

- **Who they are** — region-aware personality vectors (Lagos / Kano / Abuja / Port Harcourt / Ibadan / Enugu)
- **How they buy** — value-consciousness, social-proof sensitivity, fake-product suspicion, payment-method preference
- **How they write** — linguistic style (Yoruba-English, Pidgin, formal, code-switching)
- **Why they change** — temporal behavioural drift, emotional state evolution

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     ORACLE-X/N System                        │
│                                                              │
│  ┌───────────────┐    ┌──────────────┐   ┌───────────────┐  │
│  │  LLM Client   │    │  Memory      │   │  Graph        │  │
│  │  (Groq/OpenAI │◄──►│  Engine      │◄─►│  Engine       │  │
│  │   /Ollama)    │    │  (SQLite +   │   │  (NetworkX    │  │
│  └───────────────┘    │   Cache)     │   │   DiGraph)    │  │
│         │             └──────────────┘   └───────────────┘  │
│         ▼                    ▲                   ▲           │
│  ┌───────────────┐    ┌──────┴───────┐   ┌───────┴───────┐  │
│  │  Review       │    │  Retrieval   │   │  Nigerian     │  │
│  │  Engine       │    │  Engine      │   │  Context      │  │
│  │  (Task A)     │    │  (ChromaDB)  │   │  Layer        │  │
│  └───────────────┘    └──────────────┘   └───────────────┘  │
│         │                                                     │
│  ┌───────────────┐    ┌──────────────┐                       │
│  │ Recommendation│    │  FastAPI     │                       │
│  │  Engine       │───►│  REST API    │                       │
│  │  (Task B)     │    │  + Swagger   │                       │
│  └───────────────┘    └──────────────┘                       │
└─────────────────────────────────────────────────────────────┘
```

| Component | Technology | Purpose |
|---|---|---|
| LLM (main) | Groq `llama-3.3-70b-versatile` | Blocking JSON, review metadata, reranking |
| LLM (fast) | Groq `llama-3.1-8b-instant` | Streaming chat, review text generation |
| Embeddings | sentence-transformers/all-MiniLM-L6-v2 (384-dim) | Semantic search |
| Vector store | ChromaDB (cosine similarity, persisted) | Item & profile retrieval |
| Graph | NetworkX DiGraph + temporal decay (0.85) | Behavioural history |
| Database | SQLite via SQLAlchemy | Profile & interaction storage |
| API | FastAPI + Pydantic v2 | REST interface |
| Demo | Streamlit (5 tabs) | Interactive showcase |

---

## Quick Start

### 1. Prerequisites

- Python 3.11+
- [Groq API key](https://console.groq.com) **or** [Ollama](https://ollama.ai) running locally
- (Optional) OpenAI API key for fallback

### 2. Clone & Install

```bash
git clone <repo-url>
cd "Oracle XN"

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate       # Windows
# source .venv/bin/activate  # Linux/macOS

pip install -r requirements.txt
```

### 3. Configure Environment

Create a `.env` file in the project root:

```env
# Primary LLM provider
LLM_PROVIDER=groq

# Groq API key (free tier at console.groq.com)
GROQ_API_KEY=gsk_your_key_here
GROQ_MODEL=llama-3.3-70b-versatile
GROQ_FAST_MODEL=llama-3.1-8b-instant

# Optional tuning
LLM_TEMPERATURE=0.75
RECOMMENDATION_COUNT=10
ENABLE_NIGERIAN_CONTEXT=true
DEFAULT_REGION=Lagos
```

### 4. Seed the Database

```bash
python scripts/seed_db.py
```

This populates:
- **SQLite** with **764 real users** (Amazon + Goodreads) + **3,495 items** with realistic ₦ Naira prices
- **ChromaDB** with item and profile embeddings
- **NetworkX graph** with historical interactions and temporal decay (γ = 0.85)

To reset and re-seed:
```bash
python scripts/seed_db.py --reset
```

### 5. Start the API

```bash
python main.py
# or
uvicorn main:app --reload --port 8000
```

Visit `http://localhost:8000/docs` for the interactive Swagger UI.

### 6. Launch the Demo

```bash
streamlit run demo/app.py
```

---

## API Reference

### Health

| Endpoint | Method | Description |
|---|---|---|
| `/` | GET | Root ping |
| `/health` | GET | System health + graph stats |

### Users

| Endpoint | Method | Description |
|---|---|---|
| `/api/v1/users/{user_id}` | GET | Fetch user profile |
| `/api/v1/users/{user_id}/history` | GET | Interaction history |
| `/api/v1/users/` | POST | Create user profile |

### Reviews (Task A)

| Endpoint | Method | Description |
|---|---|---|
| `/api/v1/reviews/generate` | POST | Generate a psychologically authentic review + rating for a user × item pair |
| `/api/v1/reviews/batch` | POST | Batch generation across multiple users/items |

**Example:**
```json
POST /api/v1/reviews/generate
{
  "user_id": "user_001",
  "item_id": "item_003",
  "context": {
    "life_event": "job_promotion",
    "occasion": "treat_yourself"
  }
}
```

### Recommendations (Task B)

| Endpoint | Method | Description |
|---|---|---|
| `/api/v1/recommendations/{user_id}` | GET | Get personalised recommendations |
| `/api/v1/recommendations/{user_id}/explain` | GET | Get recommendations with LLM reasoning traces |

---

## Dataset Loading

ORACLE-X/N supports three real-world datasets for large-scale evaluation:

### Yelp

```bash
python scripts/load_datasets.py \
  --source yelp \
  --yelp-zip "C:/path/to/Yelp-JSON.zip" \
  --limit 10000
```

### Goodreads

```bash
python scripts/load_datasets.py \
  --source goodreads \
  --goodreads-reviews "C:/path/to/goodreads_reviews_dedup.json.gz" \
  --goodreads-books "C:/path/to/goodreads_books.json.gz" \
  --limit 10000
```

### Amazon Reviews (streamed via HuggingFace)

```bash
python scripts/load_datasets.py \
  --source amazon \
  --categories "Electronics,Cell_Phones_and_Accessories" \
  --limit 5000
```

### All sources together

```bash
python scripts/load_datasets.py \
  --source all \
  --limit 5000 \
  --enrich-profiles
```

**Dry-run (no ingestion):**
```bash
python scripts/load_datasets.py --source yelp --limit 100 --no-ingest --verbose
```

---

## Evaluation

### Seed-data evaluation (no datasets needed)

```bash
python scripts/run_evaluation.py --mode seed
```

### Full dataset evaluation

```bash
# With ROUGE + RMSE + NDCG (fast)
python scripts/run_evaluation.py --mode dataset --source yelp --limit 200

# With BERTScore added (slower)
python scripts/run_evaluation.py --mode dataset --source yelp --limit 200 --bert

# Save report
python scripts/run_evaluation.py --mode seed --output reports/eval_report.json
```

### Metrics computed

| Metric | Competition Weight | Measured Score | Notes |
|---|---|---|---|
| ROUGE-1/2/L | 30 pts | 0.115 / 0.009 / 0.067 | 15 LLM-generated vs ground-truth Amazon reviews; low due to Nigerian linguistic style divergence (expected) |
| BERTScore F1 | (part of 30 pts) | **0.905** | Semantic review quality (RoBERTa-large) — primary quality signal |
| **RMSE** | **25 pts** | **0.8992** | 40 users / 79 interactions across 9 Amazon categories + Goodreads |
| MAE | — | **0.4861** | Mean absolute rating error |
| Behavioural Fidelity | 20 pts | **1.000** diversity | Avg category diversity ratio across 36 users |
| Category Entropy | Task B | **1.584 bits** | Recommendation variety |
| Unique categories/rec | Task B | **4–5 / 10** | Personalised across 8 item categories |

> **Evaluation date:** 2026-05-22 — 9 Amazon categories + Goodreads, **764 users, 3,495 items** (reloaded dataset).

---

## Nigerian Context Layer

The Nigerian context is the core differentiator of ORACLE-X/N.

### Regional Behavioural Profiles

| Region | Personality Traits | Linguistic Style |
|---|---|---|
| **Lagos** | High hustle mentality, price-savvy, brand-conscious, fast-paced | Yoruba-English code-switching, Pidgin |
| **Kano** | Conservative spending, high trust threshold, bulk-buy preference | Hausa-English, formal |
| **Abuja** | Status-driven, premium preference, government/civil-service context | Professional English |
| **Port Harcourt** | Oil economy awareness, practical buyer, infrastructure-conscious | Rivers Pidgin, English |
| **Ibadan** | Community-oriented, academic culture, value-hunter | Yoruba-English, scholarly |
| **Enugu** | Igbo entrepreneurial spirit, quality-focused, diaspora awareness | Igbo-English, direct |

### Behavioural Archetypes

8 data-driven archetypes inferred from review history:

- `value_hunter` — price-sensitive, waits for deals
- `status_shopper` — brand and luxury focus
- `community_buyer` — relies heavily on social proof
- `trust_seeker` — reads every review, verifies everything
- `festive_splurger` — seasonal spike behaviour
- `tech_enthusiast` — early adopter, specs-driven
- `practical_buyer` — durability over aesthetics
- `experience_chaser` — services/experiences over products

### Dataset Mapping

US cities from Yelp/Amazon are automatically mapped to Nigerian regional profiles:

```
New York City → Lagos     |  Phoenix → Kano
Los Angeles → Lagos       |  Seattle → Abuja
Houston → Port Harcourt   |  Nashville → Ibadan
Charlotte → Abuja         |  Portland → Enugu
Pittsburgh → Port Harcourt|  Memphis → Kano
```

---

## Docker Deployment

```bash
# Build and start (images are cached after first build)
docker-compose up --build -d

# API  → http://localhost:8100   (mapped from internal 8000)
# Demo → http://localhost:8501
# Docs → http://localhost:8100/docs
```

The Dockerfile uses BuildKit pip-cache mounts so that a dropped network
connection during build resumes from where it left off rather than restarting.
PyTorch (CPU-only wheel, ~190 MB) is installed in a separate committed layer
so future rebuilds skip it entirely.

```yaml
# docker-compose.yml services:
#   oracle-api  — FastAPI on host port 8100 (internal 8000)
#   oracle-demo — Streamlit on host port 8501
# Both share a named volume 'oracle-data' at /data for SQLite + ChromaDB
```

> **Port note**: host port 8000 is reserved for VerifyNG in the same Docker
> daemon. ORACLE-X/N API is mapped to **8100**.

---

## Project Structure

```
Oracle XN/
├── main.py                   # FastAPI entrypoint
├── config.py                 # Pydantic settings (env-based)
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
│
├── api/
│   ├── dependencies.py       # FastAPI dependency injection
│   └── routes/
│       ├── health.py
│       ├── users.py
│       ├── reviews.py        # Task A endpoints
│       └── recommendations.py # Task B endpoints
│
├── engine/
│   ├── llm_client.py         # Groq / OpenAI / Ollama abstraction
│   ├── memory_engine.py      # SQLite profile + interaction store
│   ├── graph_engine.py       # NetworkX behavioural graph
│   ├── retrieval_engine.py   # ChromaDB semantic search
│   ├── review_engine.py      # Task A: review + rating generation
│   └── recommendation_engine.py  # Task B: personalised recs
│
├── models/
│   ├── user.py               # UserProfile, PersonalityVector, EmotionalState
│   ├── item.py               # Item, ItemInteraction
│   ├── schemas.py            # API request/response schemas
│   └── database.py           # SQLAlchemy engine + session
│
├── data/
│   ├── nigerian_context.py   # Regional profiles, archetypes, dataset mappers
│   ├── seed_data.py          # 7 personas + 20 products
│   └── loaders/
│       ├── base_loader.py    # DatasetRecord, BaseDatasetLoader, train/test split
│       ├── yelp_loader.py    # Yelp dataset loader
│       ├── goodreads_loader.py # Goodreads loader
│       └── amazon_loader.py  # Amazon Reviews (HuggingFace)
│
├── prompts/
│   ├── system_prompts.py     # Core persona + system prompts
│   ├── review_prompts.py     # Task A generation prompts
│   └── recommendation_prompts.py  # Task B reasoning prompts
│
├── scripts/
│   ├── seed_db.py            # One-time DB + vector store seeding
│   ├── load_datasets.py      # Dataset ingestion pipeline
│   └── run_evaluation.py     # Competition metric evaluation runner
│
├── utils/
│   ├── seeder.py             # Seeding orchestration
│   └── evaluator.py          # ROUGE, BERTScore, RMSE, NDCG, HitRate
│
└── demo/
    └── app.py                # Streamlit 5-tab interactive demo
```

---

## Reproducibility Checklist

- [x] `requirements.txt` — all dependencies pinned with `>=` minimum versions
- [x] `scripts/seed_db.py --reset` — deterministic DB reset
- [x] `scripts/load_datasets.py` — dataset paths configurable via CLI args or env vars
- [x] `config.py` — all settings overridable via `.env`
- [x] `docker-compose.yml` — full containerised deployment
- [x] `scripts/run_evaluation.py` — reproducible metric computation
- [x] `chroma_db/` — pre-seeded vector store (committed for quick start)
- [x] `oracle_graph.pkl` — pre-seeded interaction graph

---

## Run Commands Summary

```bash
# Install
pip install -r requirements.txt

# Seed
python scripts/seed_db.py

# API server
python main.py                          # default port 8000 (local), 8100 in Docker

# Demo frontend
streamlit run demo/app.py

# Load dataset
python scripts/load_datasets.py --source yelp --limit 5000

# Evaluate
python scripts/run_evaluation.py --mode seed
python scripts/run_evaluation.py --mode dataset --source yelp --limit 200 --bert

# Docker
docker-compose up --build -d          # API → :8100, Demo → :8501
```

---

## Competition Scoring Map

| Category | Max Pts | ORACLE-X/N Approach |
|---|---|---|
| ROUGE/BERTScore | 30 | LLM-generated reviews conditioned on full personality vector |
| RMSE | 25 | Multi-factor rating prediction: sentiment + personality + social norms |
| Behavioural Fidelity | 20 | 8 archetypes × 6 regional profiles × temporal drift |
| Solution Paper | 15 | `solution_paper.md` |
| Code Reproducibility | 10 | Docker + seed scripts + full CLI |
| **Total** | **100** | |

---

## License

MIT — see `LICENSE` for details.
