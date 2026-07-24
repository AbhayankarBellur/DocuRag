"""Batch Processing API Endpoints"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.services.batch_service import BatchService
from app.main import get_db, get_current_user

router = APIRouter()


@router.post("/documents", status_code=status.HTTP_202_ACCEPTED)
async def batch_upload_documents(
    files: List[UploadFile] = File(...),
    deferred: bool = False,
    defer_until: str = None,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Batch upload multiple documents"""
    batch_service = BatchService(db)
    try:
        task_id = await batch_service.batch_upload_documents(
            files=files,
            user_id=current_user.id,
            deferred=deferred,
            defer_until=defer_until
        )
        return {"task_id": task_id, "status": "processing"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/status/{task_id}")
async def get_batch_status(
    task_id: str,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get batch processing status"""
    batch_service = BatchService(db)
    status = await batch_service.get_task_status(task_id, current_user.id)
    
    if not status:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    return status


@router.post("/queries", status_code=status.HTTP_202_ACCEPTED)
async def batch_process_queries(
    queries: List[str],
    deferred: bool = False,
    defer_until: str = None,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Batch process multiple queries"""
    batch_service = BatchService(db)
    try:
        task_id = await batch_service.batch_process_queries(
            queries=queries,
            user_id=current_user.id,
            deferred=deferred,
            defer_until=defer_until
        )
        return {"task_id": task_id, "status": "processing"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
