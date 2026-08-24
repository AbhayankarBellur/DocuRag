"""Document Service"""
from __future__ import annotations

import os
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import UploadFile
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.ingestion import IngestionEngine
from app.engines.registry import get_registry
from app.models.document import Document, DocumentResponse, DocumentStatus
from app.policy.engine import PolicyEngine
from app.utils.config import settings


class DocumentService:
    """Document management service with policy-driven strategy selection."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.ingestion_engine = IngestionEngine()
        self._policy = PolicyEngine()
        self._registry = get_registry()
        # Shared vector store (singleton via registry)
        self._vector_store = self._registry.get_vector_store("chroma")

    # ------------------------------------------------------------------
    # Upload
    # ------------------------------------------------------------------

    async def upload_document(
        self,
        file: UploadFile,
        user_id: str,
        title: Optional[str] = None,
        folder_id: Optional[str] = None,
        chunking_strategy: str = "auto",
        embedding_model: str = "auto",
        vector_store: str = "chroma",
    ) -> DocumentResponse:
        """
        Upload and process a document.

        Pass ``"auto"`` (or ``None``) for *chunking_strategy* / *embedding_model*
        to let the policy engine select based on document content.  Any concrete
        value (e.g. ``"semantic"``, ``"BAAI/bge-base-en-v1.5"``) is used directly.
        """
        # ── Save file ──────────────────────────────────────────────────
        upload_dir = "./Data/uploads"
        os.makedirs(upload_dir, exist_ok=True)

        file_extension = file.filename.split(".")[-1]
        file_id = str(uuid.uuid4())
        file_path = f"{upload_dir}/{file_id}.{file_extension}"

        with open(file_path, "wb") as fh:
            content_bytes = await file.read()
            fh.write(content_bytes)

        # ── Ingest (text extraction + basic analysis) ──────────────────
        ingestion_result = self.ingestion_engine.ingest_document(
            file_path=file_path,
            filename=file.filename,
            user_id=user_id,
            title=title,
        )

        # ── DB record ──────────────────────────────────────────────────
        db_document = Document(
            id=ingestion_result["id"],
            user_id=user_id,
            title=ingestion_result["title"],
            filename=ingestion_result["filename"],
            file_path=file_path,
            file_size=ingestion_result["file_size"],
            document_type=ingestion_result["document_type"],
            status=DocumentStatus.PROCESSING,
            document_metadata=ingestion_result["metadata"],
            domain=ingestion_result["domain"],
            complexity_score=ingestion_result["complexity_score"],
            language=ingestion_result["language"],
            folder_id=folder_id,
        )

        self.db.add(db_document)
        await self.db.commit()
        await self.db.refresh(db_document)

        # ── Process (chunk → embed → store) ───────────────────────────
        await self._process_document(
            document=db_document,
            content=ingestion_result["content"],
            chunking_strategy=chunking_strategy,
            embedding_model=embedding_model,
            vector_store=vector_store,
        )

        return self._to_response(db_document)

    # ------------------------------------------------------------------
    # Processing core — now policy-aware
    # ------------------------------------------------------------------

    async def _process_document(
        self,
        document: Document,
        content: str,
        chunking_strategy: str = "auto",
        embedding_model: str = "auto",
        vector_store: str = "chroma",
    ) -> None:
        """
        Chunk, embed, and store a document.

        *chunking_strategy* and *embedding_model* accept ``"auto"`` to trigger
        policy-based selection; any other value is used directly.
        """
        print(
            f"DEBUG: _process_document start doc={document.id} "
            f"chunking={chunking_strategy} embedding={embedding_model} "
            f"store={vector_store}",
            flush=True,
        )
        try:
            # ── Resolve strategies via policy engine ───────────────────
            workflow = self._policy.resolve_workflow(
                document_content=content,
                document_metadata=document.document_metadata,
                chunking_strategy=chunking_strategy,
                embedding_model=embedding_model,
            )

            resolved_chunking = workflow.chunking_strategy
            resolved_embedding = workflow.embedding_model

            print(
                f"DEBUG: Resolved — chunking='{resolved_chunking}' "
                f"({workflow.chunking_mode.value}), "
                f"embedding='{resolved_embedding}' "
                f"({workflow.embedding_mode.value})",
                flush=True,
            )
            if workflow.auto_rationale:
                for key, reason in workflow.auto_rationale.items():
                    print(f"DEBUG: rationale[{key}]: {reason}", flush=True)

            # ── Get engines from registry ──────────────────────────────
            chunker = self._registry.get_chunking(resolved_chunking)
            embedder = self._registry.get_embedding(resolved_embedding)
            store = self._registry.get_vector_store(vector_store)

            # ── Chunk ──────────────────────────────────────────────────
            chunks = chunker.chunk(content)
            print(f"DEBUG: {len(chunks)} chunks produced", flush=True)

            # ── Embed ──────────────────────────────────────────────────
            texts = [chunk["text"] for chunk in chunks]
            embeddings = embedder.embed_batch(texts)
            print(f"DEBUG: {len(embeddings)} embeddings generated", flush=True)

            # ── Store ──────────────────────────────────────────────────
            ids = [f"{document.id}_{i}" for i in range(len(chunks))]
            metadatas = [
                {
                    "document_id": str(document.id),
                    "user_id": str(document.user_id),
                    **chunk["metadata"],
                }
                for chunk in chunks
            ]
            store.add_documents(embeddings, texts, metadatas, ids)
            print("DEBUG: vector store add completed", flush=True)

            # ── Update DB record with actual resolved config ───────────
            document.chunk_count = len(chunks)
            document.chunking_strategy = resolved_chunking
            document.embedding_model = resolved_embedding
            document.vector_store = vector_store
            document.domain = workflow.document_domain or document.domain
            document.complexity_score = (
                workflow.document_complexity or document.complexity_score
            )
            document.status = DocumentStatus.COMPLETED
            document.processed_at = datetime.utcnow()

            await self.db.commit()
            print("DEBUG: document commit completed", flush=True)

        except Exception as exc:
            print(
                f"ERROR: document processing failed for {document.id}: {exc}",
                flush=True,
            )
            document.status = DocumentStatus.FAILED
            await self.db.commit()
            raise

    # ------------------------------------------------------------------
    # CRUD helpers
    # ------------------------------------------------------------------

    def _to_response(self, document: Document) -> DocumentResponse:
        data = dict(document.__dict__)
        data.pop("_sa_instance_state", None)
        data.setdefault("updated_at", None)
        if "document_metadata" in data:
            data["metadata"] = data.pop("document_metadata")
        return DocumentResponse.model_validate(data)

    async def list_documents(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> List[DocumentResponse]:
        result = await self.db.execute(
            select(Document)
            .where(Document.user_id == user_id)
            .offset(skip)
            .limit(limit)
            .order_by(Document.created_at.desc())
        )
        return [DocumentResponse.model_validate(doc) for doc in result.scalars().all()]

    async def get_document(
        self,
        document_id: str,
        user_id: str,
    ) -> Optional[DocumentResponse]:
        result = await self.db.execute(
            select(Document).where(
                Document.id == document_id,
                Document.user_id == user_id,
            )
        )
        document = result.scalar_one_or_none()
        return DocumentResponse.model_validate(document) if document else None

    async def delete_document(
        self,
        document_id: str,
        user_id: str,
    ) -> bool:
        result = await self.db.execute(
            select(Document).where(
                Document.id == document_id,
                Document.user_id == user_id,
            )
        )
        document = result.scalar_one_or_none()
        if not document:
            return False

        try:
            if document.chunk_count and document.chunk_count > 0:
                chunk_ids = [
                    f"{document_id}_{i}" for i in range(document.chunk_count)
                ]
                try:
                    self._vector_store.delete(chunk_ids)
                except Exception as exc:
                    print(
                        f"WARNING: Failed to delete chunks from vector store: {exc}",
                        flush=True,
                    )

            if document.file_path and os.path.exists(document.file_path):
                try:
                    os.remove(document.file_path)
                except Exception as exc:
                    print(f"WARNING: Failed to delete file: {exc}", flush=True)

            await self.db.execute(
                delete(Document).where(Document.id == document_id)
            )
            await self.db.commit()
            return True

        except Exception as exc:
            print(
                f"ERROR: Failed to delete document {document_id}: {exc}", flush=True
            )
            await self.db.rollback()
            raise

    async def update_document(
        self,
        document_id: str,
        user_id: str,
        update_data: dict,
    ) -> Optional[DocumentResponse]:
        result = await self.db.execute(
            select(Document).where(
                Document.id == document_id,
                Document.user_id == user_id,
            )
        )
        document = result.scalar_one_or_none()
        if not document:
            return None

        for key, value in update_data.items():
            if key == "metadata":
                key = "document_metadata"
            if hasattr(document, key):
                setattr(document, key, value)

        await self.db.commit()
        await self.db.refresh(document)
        return DocumentResponse.model_validate(document)
