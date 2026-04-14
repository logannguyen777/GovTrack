"""backend/src/api/documents.py"""
from fastapi import APIRouter, HTTPException

from ..auth import CurrentUser
from ..database import gremlin_submit, oss_get_signed_url
from ..models.schemas import DocumentResponse

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.get("/{doc_id}", response_model=DocumentResponse)
async def get_document(doc_id: str, user: CurrentUser):
    """Get document metadata."""
    result = gremlin_submit(
        "g.V().has('Document', 'doc_id', did).valueMap(true)", {"did": doc_id},
    )
    if not result:
        raise HTTPException(status_code=404, detail="Document not found")
    props = result[0]
    return DocumentResponse(
        doc_id=doc_id,
        filename=props.get("filename", [""])[0],
        content_type=props.get("content_type", [""])[0],
        page_count=props.get("page_count", [None])[0],
        ocr_status=props.get("ocr_status", ["pending"])[0],
        oss_key=props.get("oss_key", [""])[0],
    )


@router.get("/{doc_id}/signed-url")
async def get_document_url(doc_id: str, user: CurrentUser):
    """Get a pre-signed download URL for a document."""
    result = gremlin_submit(
        "g.V().has('Document', 'doc_id', did).values('oss_key')", {"did": doc_id},
    )
    if not result:
        raise HTTPException(status_code=404, detail="Document not found")
    url = oss_get_signed_url(result[0])
    return {"doc_id": doc_id, "signed_url": url, "expires_in": 3600}
