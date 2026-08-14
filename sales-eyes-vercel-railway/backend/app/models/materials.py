import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, func, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class CompanyMaterial(Base):
    __tablename__ = "company_materials"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("research_sessions.id", ondelete="CASCADE"), nullable=False)

    material_type: Mapped[str] = mapped_column(String(50), nullable=False)  # brochure | sales_script | product_info | custom
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    file_size: Mapped[int] = mapped_column(nullable=False)  # in bytes
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)

    content_text: Mapped[str | None] = mapped_column(Text, nullable=True)  # extracted/processed content
    description: Mapped[str | None] = mapped_column(Text, nullable=True)  # user's description of the material

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
