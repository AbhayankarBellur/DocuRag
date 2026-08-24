"""
Policy API
----------
Endpoints that expose the auto-selection policy to the UI so it can:

  * Show the user what strategies would be auto-selected before they submit.
  * Populate dropdowns with all available strategy options.
  * Let the user preview a workflow given a query string and/or document text.

Routes
------
GET  /api/policy/options
    Returns all valid values for every strategy axis.

POST /api/policy/workflow-preview
    Returns the fully-resolved WorkflowConfig for the supplied inputs *without*
    executing any retrieval or generation.  Useful for showing the user exactly
    what auto-selection would pick before they commit.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.dependencies import get_current_user
from app.engines.registry import EngineRegistry
from app.policy.engine import PolicyEngine

router = APIRouter()

# Module-level singletons (cheap — no model loading happens here)
_policy = PolicyEngine()


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class WorkflowPreviewRequest(BaseModel):
    """
    Inputs for a workflow preview.

    All fields are optional — supply whichever combination you have available.
    Pass ``"auto"`` or omit a strategy field to let the policy engine decide.
    """

    # Content signals
    query: Optional[str] = Field(
        default=None,
        description="Query text — drives retrieval, reranking, and prompt template selection.",
    )
    document_text_sample: Optional[str] = Field(
        default=None,
        description=(
            "A representative sample of the document text (first ~2 000 chars is "
            "plenty) — drives chunking and embedding selection."
        ),
    )

    # Optional explicit overrides (None / 'auto' → let policy decide)
    chunking_strategy: Optional[str] = Field(
        default=None,
        description="fixed | recursive | semantic | section | auto",
    )
    embedding_model: Optional[str] = Field(
        default=None,
        description="BAAI/bge-small-en-v1.5 | bge-base | bge-large | auto",
    )
    retrieval_strategy: Optional[str] = Field(
        default=None,
        description="similarity | hybrid | mmr | auto",
    )
    reranking_strategy: Optional[str] = Field(
        default=None,
        description="bm25 | cross_encoder | cohere | none | auto",
    )
    prompt_template: Optional[str] = Field(
        default=None,
        description="factual_qa | analysis | comparison | creative | auto",
    )


class WorkflowPreviewResponse(BaseModel):
    """Resolved workflow — what the system would actually use."""

    chunking_strategy: str
    chunking_mode: str          # "auto" or "manual"
    embedding_model: str
    embedding_mode: str
    retrieval_strategy: str
    retrieval_mode: str
    reranking_strategy: Optional[str]
    reranking_mode: str
    prompt_template: str
    prompt_mode: str
    generation_params: Dict[str, Any]
    auto_rationale: Dict[str, str]
    document_domain: Optional[str]
    document_complexity: Optional[int]
    query_intent: Optional[str]
    query_complexity: Optional[int]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/options",
    summary="List all available strategy options",
    response_model=Dict[str, Any],
)
async def get_policy_options(
    _current_user=Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Return the complete set of valid values for every strategy axis.

    The UI uses this to populate dropdowns and validate user input.

    Each list includes ``"auto"`` as the first entry so the UI can always
    offer the auto-selection option.
    """
    options = EngineRegistry.available_options()

    # Prepend "auto" to every list so the UI can always offer it
    return {
        key: (["auto"] + values) if "auto" not in values else values
        for key, values in options.items()
    }


@router.post(
    "/workflow-preview",
    summary="Preview auto-selected workflow without executing it",
    response_model=WorkflowPreviewResponse,
)
async def preview_workflow(
    request: WorkflowPreviewRequest,
    _current_user=Depends(get_current_user),
) -> WorkflowPreviewResponse:
    """
    Resolve and return the workflow the system would use for the supplied inputs.

    No retrieval, embedding, or generation is performed — this is a pure
    policy-engine call intended for UI previews and debugging.

    **How to use from the UI**

    * On the *upload* screen: send ``document_text_sample`` (with optional
      ``chunking_strategy`` / ``embedding_model`` overrides) to preview what
      the ingestion pipeline would select.
    * On the *query* screen: send ``query`` (with optional
      ``retrieval_strategy`` / ``reranking_strategy`` / ``prompt_template``
      overrides) to see what the retrieval pipeline would use.
    * Combine both to get a complete end-to-end preview.
    """
    workflow = _policy.resolve_workflow(
        document_content=request.document_text_sample,
        query=request.query,
        chunking_strategy=request.chunking_strategy,
        embedding_model=request.embedding_model,
        retrieval_strategy=request.retrieval_strategy,
        reranking_strategy=request.reranking_strategy,
        prompt_template=request.prompt_template,
    )

    return WorkflowPreviewResponse(**workflow.to_dict())
