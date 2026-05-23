"""
ORACLE-X/N — Health & System Status Routes
=============================================
"""

from datetime import datetime

from fastapi import APIRouter, Depends

from api.dependencies import (
    get_graph_engine,
    get_memory_engine,
    get_settings,
    get_retrieval_engine,
)
from models.schemas import HealthResponse

router = APIRouter()


@router.get("/", summary="Root ping")
async def root():
    return {"message": "ORACLE-X/N is alive. Behavioural intelligence ready."}


@router.get("/health", response_model=HealthResponse, summary="System health check")
async def health_check(
    settings=Depends(get_settings),
    memory=Depends(get_memory_engine),
    graph=Depends(get_graph_engine),
    retrieval=Depends(get_retrieval_engine),
):
    user_ids = memory.list_all_user_ids()
    return HealthResponse(
        status="ok",
        version="1.0.0",
        llm_provider=settings.llm_provider,
        graph_nodes=graph.node_count,
        graph_edges=graph.edge_count,
        total_users=len(user_ids),
        total_items=memory.get_item_count(),
        timestamp=datetime.utcnow(),
    )
