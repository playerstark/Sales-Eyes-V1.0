import uuid
import os
import mimetypes
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.config import settings
from app.models.user import User
from app.models.materials import CompanyMaterial
from app.models.research import ResearchSession
from app.models.schemas import CompanyMaterialOut, CompanyMaterialCreate

router = APIRouter(prefix="/api/materials", tags=["materials"])

# Create uploads directory if it doesn't exist
UPLOAD_DIR = Path(settings.BASE_DIR or "/tmp") / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def extract_text_from_file(file_path: str) -> str:
    """Extract text content from an uploaded product/company material so it
    can ground sales-script generation. Supports plain text, PDF, and Word
    documents — the common formats for a "here's info about our product"
    upload."""
    lower = file_path.lower()
    try:
        if lower.endswith((".txt", ".md", ".csv")):
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()

        if lower.endswith(".pdf"):
            from pypdf import PdfReader
            reader = PdfReader(file_path)
            return "\n".join(page.extract_text() or "" for page in reader.pages)

        if lower.endswith(".docx"):
            import docx
            doc = docx.Document(file_path)
            return "\n".join(p.text for p in doc.paragraphs)

        # Unsupported binary type (e.g. .doc, images) — no text extraction
        # available; the material is still stored and listed, just without
        # content_text for the AI to read.
        return ""
    except Exception:
        return ""


@router.post("/upload")
async def upload_material(
    session_id: uuid.UUID = Form(...),
    material_type: str = Form(...),
    name: str = Form(...),
    file: UploadFile = File(...),
    description: str | None = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Upload a company material (brochure, sales script, product info).

    Accepts session_id/material_type/name/description as multipart form
    fields (matching what the frontend's FormData actually sends) rather
    than query params.
    """
    file_path = None

    try:
        # Validate session ownership
        session = await db.get(ResearchSession, session_id)
        if not session or session.owner_id != current_user.id:
            raise HTTPException(status_code=404, detail="Session not found")

        # Validate material type
        valid_types = ["brochure", "sales_script", "product_info", "custom"]
        if material_type not in valid_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid material type. Must be one of: {', '.join(valid_types)}"
            )

        # Validate file extension
        filename = file.filename or "unknown"
        file_ext = Path(filename).suffix.lower()
        allowed_exts = [".pdf", ".docx", ".txt", ".md"]
        if file_ext not in allowed_exts:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Supported: {', '.join(allowed_exts)}"
            )

        # Limit file size (10MB for frontend, enforced here too)
        max_size = 10 * 1024 * 1024
        if file.size and file.size > max_size:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum size: 10MB"
            )

        # Generate safe file path
        safe_filename = f"{uuid.uuid4()}{file_ext}"
        file_path = UPLOAD_DIR / safe_filename

        # Save file
        content = await file.read()

        if not content:
            raise HTTPException(status_code=400, detail="File is empty")

        with open(file_path, "wb") as f:
            f.write(content)

        # Extract text if possible
        content_text = extract_text_from_file(str(file_path))

        if not content_text:
            raise HTTPException(
                status_code=400,
                detail="Could not extract text from file. Ensure file is not corrupted or image-only."
            )

        # Create database record
        material = CompanyMaterial(
            owner_id=current_user.id,
            session_id=session_id,
            material_type=material_type,
            name=name,
            file_path=str(file_path),
            file_size=len(content),
            mime_type=file.content_type or "application/octet-stream",
            content_text=content_text if content_text else None,
            description=description
        )
        db.add(material)
        await db.commit()
        await db.refresh(material)

        return CompanyMaterialOut.model_validate(material)

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        if file_path and file_path.exists():
            file_path.unlink()
        raise
    except Exception as e:
        if file_path and file_path.exists():
            file_path.unlink()
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.get("/session/{session_id}")
async def list_materials(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all materials for a research session."""
    session = await db.get(ResearchSession, session_id)
    if not session or session.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Session not found")

    result = await db.execute(
        select(CompanyMaterial).where(CompanyMaterial.session_id == session_id)
    )
    materials = result.scalars().all()

    return {
        "materials": [CompanyMaterialOut.model_validate(m) for m in materials]
    }


@router.get("/{material_id}")
async def get_material(
    material_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific material."""
    material = await db.get(CompanyMaterial, material_id)
    if not material or material.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Material not found")

    return CompanyMaterialOut.model_validate(material)


@router.delete("/{material_id}")
async def delete_material(
    material_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a material."""
    material = await db.get(CompanyMaterial, material_id)
    if not material or material.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Material not found")

    # Delete file
    if material.file_path and Path(material.file_path).exists():
        Path(material.file_path).unlink()

    # Delete database record
    await db.delete(material)
    await db.commit()

    return {"status": "deleted"}
