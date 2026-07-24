"""Queries API Endpoints"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.models.query import QueryCreate, QueryResponse, BatchQueryCreate, BatchQueryResponse
from app.services.query_service import QueryService
from app.main import get_db, get_current_user

router = APIRouter()


@router.post("/", response_model=QueryResponse)
async def create_query(
    query_data: QueryCreate,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create and execute a query"""
    query_service = QueryService(db)
    try:
        result = await query_service.process_query(
            query_data=query_data,
            user_id=current_user.id
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/history", response_model=List[QueryResponse])
async def get_query_history(
    skip: int = 0,
    limit: int = 100,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user's query history"""
    query_service = QueryService(db)
    queries = await query_service.get_query_history(
        user_id=current_user.id,
        skip=skip,
        limit=limit
    )
    return queries


@router.get("/{query_id}", response_model=QueryResponse)
async def get_query(
    query_id: str,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific query"""
    query_service = QueryService(db)
    query = await query_service.get_query(query_id, current_user.id)
    
    if not query:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Query not found"
        )
    
    return query


@router.post("/batch", response_model=BatchQueryResponse)
async def create_batch_query(
    batch_data: BatchQueryCreate,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a batch of queries"""
    query_service = QueryService(db)
    try:
        result = await query_service.process_batch_query(
            batch_data=batch_data,
            user_id=current_user.id
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
