"""
Knowledge base management — document upload and ingestion into Milvus.
"""

import io
import structlog
from typing import List

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File

from ...security.auth import get_current_user
from ...knowledge.rag import RAGSystem

router = APIRouter()
logger = structlog.get_logger()

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md"}
MAX_FILE_SIZE_MB = 20
CHUNK_SIZE = 1000      # characters per chunk
CHUNK_OVERLAP = 150    # overlap between chunks


def _chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """Split text into overlapping chunks."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + size
        chunks.append(text[start:end])
        start += size - overlap
    return [c.strip() for c in chunks if c.strip()]


def _extract_text(filename: str, content: bytes) -> str:
    """Extract plain text from uploaded file."""
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext == ".pdf":
        try:
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(content))
            return "\n\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"Failed to parse PDF: {e}")

    # .txt and .md — decode as UTF-8
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        return content.decode("latin-1")


# Dependency — resolved from app state via a module-level reference
_rag_system: RAGSystem = None


def set_rag_system(rag: RAGSystem) -> None:
    global _rag_system
    _rag_system = rag


def get_rag_system() -> RAGSystem:
    if _rag_system is None:
        raise HTTPException(status_code=503, detail="RAG system not initialized")
    return _rag_system


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    rag: RAGSystem = Depends(get_rag_system),
):
    """
    Upload a document (PDF, TXT, MD) and index it into the knowledge base.

    The text is chunked and embedded, making it immediately searchable
    by the ResearchAgent in subsequent workflow runs.
    """
    # Validate extension
    filename = file.filename or "upload"
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed: {ALLOWED_EXTENSIONS}",
        )

    # Read and size-check
    content = await file.read()
    size_mb = len(content) / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({size_mb:.1f} MB). Max: {MAX_FILE_SIZE_MB} MB",
        )

    # Extract text
    text = _extract_text(filename, content)
    if not text.strip():
        raise HTTPException(status_code=422, detail="No text could be extracted from the file")

    # Chunk and index
    chunks = _chunk_text(text)
    documents = [
        {
            "text": chunk,
            "metadata": {
                "source": filename,
                "chunk": i,
                "uploaded_by": current_user.get("username", "unknown"),
                "type": "uploaded_document",
            },
        }
        for i, chunk in enumerate(chunks)
    ]

    try:
        await rag.add_documents(documents)
    except Exception as e:
        logger.error("Failed to index document", filename=filename, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to index document: {e}")

    logger.info("Document indexed", filename=filename, chunks=len(chunks), user=current_user.get("username"))
    return {
        "filename": filename,
        "size_mb": round(size_mb, 2),
        "characters": len(text),
        "chunks_indexed": len(chunks),
        "message": f"Successfully indexed {len(chunks)} chunks from '{filename}'",
    }


@router.get("/stats")
async def knowledge_base_stats(
    current_user: dict = Depends(get_current_user),
    rag: RAGSystem = Depends(get_rag_system),
):
    """Return basic knowledge base statistics."""
    try:
        healthy = rag.health_check()
        return {"status": "healthy" if healthy else "degraded", "collection": "artist_knowledge_base"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}
