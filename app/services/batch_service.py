"""Batch Processing Service"""
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import UploadFile
import uuid
from datetime import datetime
from app.services.document_service import DocumentService
from app.services.query_service import QueryService


class BatchService:
    """Batch processing service"""
    
    def __init__(self, db: AsyncSession):
        """
        Initialize batch service
        
        Args:
            db: Database session
        """
        self.db = db
        self.document_service = DocumentService(db)
        self.query_service = QueryService(db)
        self.tasks = {}  # In-memory task storage (use Redis in production)
    
    async def batch_upload_documents(
        self,
        files: List[UploadFile],
        user_id: str,
        deferred: bool = False,
        defer_until: str = None
    ) -> str:
        """
        Batch upload multiple documents
        
        Args:
            files: List of files to upload
            user_id: User ID
            deferred: Whether to defer processing
            defer_until: When to process if deferred
        
        Returns:
            Task ID
        """
        task_id = str(uuid.uuid4())
        
        self.tasks[task_id] = {
            "id": task_id,
            "type": "document_upload",
            "user_id": user_id,
            "status": "processing",
            "total": len(files),
            "completed": 0,
            "failed": 0,
            "created_at": datetime.utcnow(),
            "results": []
        }
        
        # Process documents
        for file in files:
            try:
                result = await self.document_service.upload_document(
                    file=file,
                    user_id=user_id
                )
                self.tasks[task_id]["completed"] += 1
                self.tasks[task_id]["results"].append(result)
            except Exception as e:
                self.tasks[task_id]["failed"] += 1
        
        self.tasks[task_id]["status"] = "completed"
        
        return task_id
    
    async def batch_process_queries(
        self,
        queries: List[str],
        user_id: str,
        deferred: bool = False,
        defer_until: str = None
    ) -> str:
        """
        Batch process multiple queries
        
        Args:
            queries: List of query strings
            user_id: User ID
            deferred: Whether to defer processing
            defer_until: When to process if deferred
        
        Returns:
            Task ID
        """
        from app.models.query import BatchQueryCreate, QueryCreate
        
        task_id = str(uuid.uuid4())
        
        self.tasks[task_id] = {
            "id": task_id,
            "type": "query_batch",
            "user_id": user_id,
            "status": "processing",
            "total": len(queries),
            "completed": 0,
            "failed": 0,
            "created_at": datetime.utcnow(),
            "results": []
        }
        
        # Convert to QueryCreate objects
        query_data_list = [QueryCreate(question=q) for q in queries]
        batch_data = BatchQueryCreate(queries=query_data_list)
        
        # Process batch
        result = await self.query_service.process_batch_query(batch_data, user_id)
        
        self.tasks[task_id]["completed"] = result.completed_queries
        self.tasks[task_id]["failed"] = result.failed_queries
        self.tasks[task_id]["results"] = result.results
        self.tasks[task_id]["status"] = "completed"
        
        return task_id
    
    async def get_task_status(
        self,
        task_id: str,
        user_id: str
    ) -> dict:
        """
        Get batch processing task status
        
        Args:
            task_id: Task ID
            user_id: User ID
        
        Returns:
            Task status
        """
        task = self.tasks.get(task_id)
        
        if not task or task["user_id"] != user_id:
            return None
        
        return {
            "task_id": task["id"],
            "type": task["type"],
            "status": task["status"],
            "total": task["total"],
            "completed": task["completed"],
            "failed": task["failed"],
            "created_at": task["created_at"]
        }
