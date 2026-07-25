"""Documents API Endpoints"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.models.document import DocumentCreate, DocumentResponse, DocumentUpdate
from app.services.document_service import DocumentService
from app.dependencies import get_db, get_current_user

router = APIRouter()


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    title: str = None,
    folder_id: str = None,
    chunking_strategy: str = "fixed",
    embedding_model: str = "BAAI/bge-small-en-v1.5",
    vector_store: str = "chroma",
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Upload a new document"""
    doc_service = DocumentService(db)
    try:
        document = await doc_service.upload_document(
            file=file,
            user_id=current_user.id,
            title=title,
            folder_id=folder_id,
            chunking_strategy=chunking_strategy,
            embedding_model=embedding_model,
            vector_store=vector_store
        )
        return document
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/list", response_model=List[DocumentResponse])
async def list_documents(
    skip: int = 0,
    limit: int = 100,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List user's documents"""
    doc_service = DocumentService(db)
    documents = await doc_service.list_documents(
        user_id=current_user.id,
        skip=skip,
        limit=limit
    )
    return documents


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific document"""
    doc_service = DocumentService(db)
    document = await doc_service.get_document(document_id, current_user.id)
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    return document


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: str,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a document"""
    doc_service = DocumentService(db)
    success = await doc_service.delete_document(document_id, current_user.id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    return None


@router.put("/{document_id}", response_model=DocumentResponse)
async def update_document(
    document_id: str,
    update_data: DocumentUpdate,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update document metadata"""
    doc_service = DocumentService(db)
    document = await doc_service.update_document(
        document_id,
        current_user.id,
        update_data.dict(exclude_unset=True)
    )
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    return document
