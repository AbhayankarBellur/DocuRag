"""Query Service"""
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
import time
from app.models.query import Query, QueryStatus, QueryResponse, QueryCreate, BatchQueryCreate, BatchQueryResponse
from app.models.document import Document
from app.engines.embedding.bge_embedding import BGEEmbedding
from app.engines.storage.chroma_storage import ChromaStorage
from app.engines.retrieval.similarity_retrieval import SimilarityRetrieval
from app.engines.generation.hf_inference import HFInference
from app.engines.prompting.template_manager import TemplateManager, PromptType
from app.utils.config import settings


class QueryService:
    """Query processing service"""
    
    def __init__(self, db: AsyncSession):
        """
        Initialize query service
        
        Args:
            db: Database session
        """
        self.db = db
        self.embedding_model = BGEEmbedding()
        self.vector_store = ChromaStorage()
        self.retrieval = SimilarityRetrieval(self.vector_store)
        self.generator = HFInference()
        self.template_manager = TemplateManager()
    
    async def process_query(
        self,
        query_data: QueryCreate,
        user_id: str
    ) -> QueryResponse:
        """
        Process a query end-to-end
        
        Args:
            query_data: Query creation data
            user_id: User ID
        
        Returns:
            Query response with answer
        """
        start_time = time.time()
        
        # Create query record
        db_query = Query(
            user_id=user_id,
            question=query_data.question,
            document_id=query_data.document_id,
            status=QueryStatus.PROCESSING
        )
        
        self.db.add(db_query)
        await self.db.commit()
        await self.db.refresh(db_query)
        
        try:
            # Generate query embedding
            query_embedding = self.embedding_model.embed_text(query_data.question)
            
            # Retrieve relevant documents
            retrieval_start = time.time()
            filters = {"user_id": user_id}
            if query_data.document_id:
                filters["document_id"] = query_data.document_id
            
            results = self.retrieval.retrieve(
                query_embedding=query_embedding,
                n_results=5,
                filters=filters
            )
            retrieval_time = int((time.time() - retrieval_start) * 1000)
            
            # Prepare context
            context = "\n\n".join([r["text"] for r in results])
            
            # Generate answer
            generation_start = time.time()
            prompt_type = PromptType.FACTUAL_QA
            prompt = self.template_manager.get_template(
                prompt_type=prompt_type,
                query=query_data.question,
                context=context
            )
            
            generation_result = self.generator.generate_with_context(
                query=query_data.question,
                context=context,
                max_tokens=512,
                temperature=0.7,
                template=prompt
            )
            generation_time = int((time.time() - generation_start) * 1000)
            
            # Update query record
            db_query.answer = generation_result["generated_text"]
            db_query.sources = [{"id": r["id"], "text": r["text"][:200]} for r in results]
            db_query.retrieval_strategy = query_data.retrieval_strategy or "similarity"
            db_query.reranking_strategy = query_data.reranking_strategy
            db_query.embedding_model = settings.embedding_model
            db_query.generation_model = settings.hf_model
            db_query.prompt_template = query_data.prompt_template or "factual_qa"
            db_query.retrieval_time = retrieval_time
            db_query.generation_time = generation_time
            db_query.total_time = int((time.time() - start_time) * 1000)
            db_query.token_usage = generation_result.get("tokens_used", 0)
            db_query.status = QueryStatus.COMPLETED
            db_query.updated_at = datetime.utcnow()
            
            await self.db.commit()
            await self.db.refresh(db_query)
            
            return QueryResponse.model_validate(db_query)
            
        except Exception as e:
            db_query.status = QueryStatus.FAILED
            db_query.error_message = str(e)
            await self.db.commit()
            raise e
    
    async def get_query_history(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[QueryResponse]:
        """Get user's query history"""
        result = await self.db.execute(
            select(Query)
            .where(Query.user_id == user_id)
            .offset(skip)
            .limit(limit)
            .order_by(Query.created_at.desc())
        )
        queries = result.scalars().all()
        return [QueryResponse.model_validate(q) for q in queries]
    
    async def get_query(
        self,
        query_id: str,
        user_id: str
    ) -> Optional[QueryResponse]:
        """Get a specific query"""
        result = await self.db.execute(
            select(Query)
            .where(Query.id == query_id, Query.user_id == user_id)
        )
        query = result.scalar_one_or_none()
        
        if query:
            return QueryResponse.model_validate(query)
        return None
    
    async def process_batch_query(
        self,
        batch_data: BatchQueryCreate,
        user_id: str
    ) -> BatchQueryResponse:
        """
        Process a batch of queries
        
        Args:
            batch_data: Batch query data
            user_id: User ID
        
        Returns:
            Batch query response
        """
        task_id = str(int(time.time()))
        
        # For now, process synchronously (in production, use Celery)
        results = []
        completed = 0
        failed = 0
        
        for query_data in batch_data.queries:
            try:
                result = await self.process_query(query_data, user_id)
                results.append(result)
                completed += 1
            except Exception as e:
                failed += 1
        
        return BatchQueryResponse(
            task_id=task_id,
            status="completed",
            total_queries=len(batch_data.queries),
            completed_queries=completed,
            failed_queries=failed,
            results=results
        )
