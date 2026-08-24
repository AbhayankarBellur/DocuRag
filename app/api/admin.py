"""Admin API Endpoints"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import UserRole, UserResponse
from app.dependencies import get_db, get_current_user

router = APIRouter()


# ─── Admin guard ──────────────────────────────────────────────────────────────
async def get_admin_user(current_user=Depends(get_current_user)):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user


# ─── Existing endpoints ───────────────────────────────────────────────────────
@router.get("/users", response_model=List[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    admin_user: UserResponse = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    return []


@router.get("/stats")
async def get_system_stats(
    admin_user: UserResponse = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    return {"total_users": 0, "total_documents": 0, "total_queries": 0, "active_users": 0}


@router.post("/policies")
async def update_policies(policy_data: dict, admin_user=Depends(get_admin_user)):
    return {"message": "Policies updated successfully"}


# ─── Evaluation endpoints ─────────────────────────────────────────────────────

class GoldenItem(BaseModel):
    question: str
    ground_truth: str
    document_id: Optional[str] = None


class EvalRunRequest(BaseModel):
    golden_items: List[GoldenItem]
    conditions: Optional[List[str]] = None   # defaults to all four


class EvalRunResultOut(BaseModel):
    condition: str
    config: Dict[str, str]
    faithfulness: float
    answer_relevancy: float
    context_precision: float
    context_recall: Optional[float]
    overall_score: float
    avg_tokens: float
    avg_latency_ms: float
    n_items: int
    ragas_placeholder: bool


class EvalRunOut(BaseModel):
    run_id: str
    results: List[EvalRunResultOut]


@router.post(
    "/evaluate",
    response_model=EvalRunOut,
    summary="Run RAGAS evaluation comparison",
    description=(
        "Executes every golden QA item under each requested condition "
        "(auto / similarity / hybrid_bm25 / mmr_cross_encoder), "
        "scores with RAGAS metrics, and returns a comparison table. "
        "If ragas is not installed, placeholder 0.0 scores are returned "
        "so the rest of the pipeline is still testable."
    ),
)
async def run_evaluation(
    request: EvalRunRequest,
    current_user=Depends(get_current_user),   # any authenticated user can run
    db: AsyncSession = Depends(get_db),
) -> EvalRunOut:
    """Run a multi-condition RAGAS evaluation."""
    from app.services.eval_service import EvalService

    if not request.golden_items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one golden item is required.",
        )

    try:
        service = EvalService(db)
        outcome = await service.run_comparison(
            golden_items=[item.model_dump() for item in request.golden_items],
            user_id=str(current_user.id),
            conditions=request.conditions,
        )
        return EvalRunOut(**outcome)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Evaluation failed: {exc}",
        )


@router.get(
    "/evaluate/history",
    summary="Evaluation run history (stub)",
    description="Returns persisted evaluation runs. Storage TBD — returns empty list until a run store is wired.",
)
async def eval_history(current_user=Depends(get_current_user)) -> List[Dict[str, Any]]:
    # Future: store runs in DB and return here
    return []
