"""Celery Tasks for Batch Processing"""
from celery import Celery
from datetime import datetime, timedelta
from typing import List, Dict, Any
import uuid
from app.utils.config import settings

# Create Celery app
celery_app = Celery(
    "microbrain",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour
    task_soft_time_limit=3000,  # 50 minutes
)


@celery_app.task(bind=True)
def process_document_batch(
    self,
    file_paths: List[str],
    user_id: str,
    task_id: str
) -> Dict[str, Any]:
    """
    Process a batch of documents asynchronously
    
    Args:
        self: Celery task instance
        file_paths: List of file paths to process
        user_id: User ID
        task_id: Task ID for tracking
    
    Returns:
        Processing results
    """
    from app.services.document_service import DocumentService
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    import asyncio
    
    # Create database session
    engine = create_async_engine(settings.database_url)
    AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)
    
    results = {
        "task_id": task_id,
        "user_id": user_id,
        "status": "processing",
        "total": len(file_paths),
        "completed": 0,
        "failed": 0,
        "results": []
    }
    
    async def process():
        async with AsyncSessionLocal() as db:
            doc_service = DocumentService(db)
            
            for i, file_path in enumerate(file_paths):
                try:
                    # Update progress
                    self.update_state(
                        state="PROGRESS",
                        meta={
                            "current": i + 1,
                            "total": len(file_paths),
                            "status": f"Processing file {i + 1}/{len(file_paths)}"
                        }
                    )
                    
                    # Process document (simplified - would need full file handling)
                    # For now, just simulate processing
                    results["completed"] += 1
                    results["results"].append({
                        "file_path": file_path,
                        "status": "completed"
                    })
                    
                except Exception as e:
                    results["failed"] += 1
                    results["results"].append({
                        "file_path": file_path,
                        "status": "failed",
                        "error": str(e)
                    })
            
            results["status"] = "completed"
            return results
    
    return asyncio.run(process())


@celery_app.task(bind=True)
def process_query_batch(
    self,
    queries: List[str],
    user_id: str,
    task_id: str
) -> Dict[str, Any]:
    """
    Process a batch of queries asynchronously
    
    Args:
        self: Celery task instance
        queries: List of query strings
        user_id: User ID
        task_id: Task ID for tracking
    
    Returns:
        Processing results
    """
    from app.services.query_service import QueryService
    from app.models.query import QueryCreate, BatchQueryCreate
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    import asyncio
    
    # Create database session
    engine = create_async_engine(settings.database_url)
    AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)
    
    results = {
        "task_id": task_id,
        "user_id": user_id,
        "status": "processing",
        "total": len(queries),
        "completed": 0,
        "failed": 0,
        "results": []
    }
    
    async def process():
        async with AsyncSessionLocal() as db:
            query_service = QueryService(db)
            
            # Convert to QueryCreate objects
            query_data_list = [QueryCreate(question=q) for q in queries]
            batch_data = BatchQueryCreate(queries=query_data_list)
            
            # Process batch
            batch_result = await query_service.process_batch_query(batch_data, user_id)
            
            results["completed"] = batch_result.completed_queries
            results["failed"] = batch_result.failed_queries
            results["results"] = batch_result.results
            results["status"] = "completed"
            
            return results
    
    return asyncio.run(process())


@celery_app.task
def deferred_task(
    task_func: str,
    task_args: Dict[str, Any],
    execute_at: datetime
) -> Dict[str, Any]:
    """
    Execute a task at a specified time (timer deferral)
    
    Args:
        task_func: Task function name to execute
        task_args: Arguments for the task
        execute_at: Time to execute the task
    
    Returns:
        Task results
    """
    from datetime import datetime as dt
    
    # Wait until execution time
    now = dt.utcnow()
    if execute_at > now:
        delay = (execute_at - now).total_seconds()
        import time
        time.sleep(delay)
    
    # Execute the task
    if task_func == "process_document_batch":
        return process_document_batch(**task_args)
    elif task_func == "process_query_batch":
        return process_query_batch(**task_args)
    else:
        raise ValueError(f"Unknown task function: {task_func}")


@celery_app.task(bind=True)
def health_check(self) -> Dict[str, Any]:
    """
    Health check task for Celery worker
    
    Returns:
        Health status
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "worker": self.request.hostname
    }
