"""Celery Service for Task Management"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from app.tasks.celery_tasks import celery_app, process_document_batch, process_query_batch, deferred_task


class CeleryService:
    """Service for managing Celery tasks"""
    
    def __init__(self):
        """Initialize Celery service"""
        self.celery_app = celery_app
    
    def schedule_document_batch(
        self,
        file_paths: List[str],
        user_id: str,
        deferred: bool = False,
        defer_until: Optional[datetime] = None
    ) -> str:
        """
        Schedule a document batch processing task
        
        Args:
            file_paths: List of file paths to process
            user_id: User ID
            deferred: Whether to defer processing
            defer_until: When to process if deferred
        
        Returns:
            Task ID
        """
        task_id = str(uuid.uuid4())
        
        task_args = {
            "file_paths": file_paths,
            "user_id": user_id,
            "task_id": task_id
        }
        
        if deferred:
            if defer_until is None:
                defer_until = datetime.utcnow() + timedelta(hours=1)
            
            # Schedule deferred task
            task = deferred_task.apply_async(
                args=["process_document_batch", task_args, defer_until],
                eta=defer_until
            )
        else:
            # Execute immediately
            task = process_document_batch.apply_async(
                kwargs=task_args
            )
        
        return task.id
    
    def schedule_query_batch(
        self,
        queries: List[str],
        user_id: str,
        deferred: bool = False,
        defer_until: Optional[datetime] = None
    ) -> str:
        """
        Schedule a query batch processing task
        
        Args:
            queries: List of query strings
            user_id: User ID
            deferred: Whether to defer processing
            defer_until: When to process if deferred
        
        Returns:
            Task ID
        """
        task_id = str(uuid.uuid4())
        
        task_args = {
            "queries": queries,
            "user_id": user_id,
            "task_id": task_id
        }
        
        if deferred:
            if defer_until is None:
                defer_until = datetime.utcnow() + timedelta(hours=1)
            
            # Schedule deferred task
            task = deferred_task.apply_async(
                args=["process_query_batch", task_args, defer_until],
                eta=defer_until
            )
        else:
            # Execute immediately
            task = process_query_batch.apply_async(
                kwargs=task_args
            )
        
        return task.id
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the status of a task
        
        Args:
            task_id: Task ID
        
        Returns:
            Task status information
        """
        result = self.celery_app.AsyncResult(task_id)
        
        return {
            "task_id": task_id,
            "status": result.status,
            "result": result.result if result.ready() else None,
            "info": result.info if result.status == "FAILURE" else None
        }
    
    def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a task
        
        Args:
            task_id: Task ID
        
        Returns:
            True if cancelled successfully
        """
        result = self.celery_app.AsyncResult(task_id)
        return result.revoke(terminate=True)
    
    def get_worker_stats(self) -> Dict[str, Any]:
        """
        Get statistics about Celery workers
        
        Returns:
            Worker statistics
        """
        inspect = self.celery_app.control.inspect()
        
        stats = {
            "active": inspect.active(),
            "scheduled": inspect.scheduled(),
            "registered": inspect.registered(),
            "stats": inspect.stats()
        }
        
        return stats
