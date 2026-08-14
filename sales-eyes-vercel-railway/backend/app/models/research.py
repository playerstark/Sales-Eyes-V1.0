import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import String, Boolean, DateTime, func, Integer, ForeignKey, DECIMAL, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ResearchSession(Base):
    __tablename__ = "research_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    prospect_input: Mapped[str] = mapped_column(Text, nullable=False)
    prospect_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    prospect_company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    prospect_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    research_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="planning", nullable=False)  # planning | executing | completed | failed
    plan: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    findings: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    selected_finding_ids: Mapped[list[uuid.UUID]] = mapped_column(ARRAY(UUID(as_uuid=True)), default=list, nullable=False)
    methodology: Mapped[str | None] = mapped_column(String(100), nullable=True)
    generated_output: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    plan_steps: Mapped[list["PlanStep"]] = relationship("PlanStep", cascade="all, delete-orphan")
    findings_rel: Mapped[list["Finding"]] = relationship("Finding", cascade="all, delete-orphan")


class PlanStep(Base):
    __tablename__ = "plan_steps"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("research_sessions.id", ondelete="CASCADE"), nullable=False)
    step_order: Mapped[int] = mapped_column(Integer, nullable=False)
    agent_type: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)  # pending | in_progress | completed | failed
    result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Finding(Base):
    __tablename__ = "findings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("research_sessions.id", ondelete="CASCADE"), nullable=False)
    plan_step_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("plan_steps.id", ondelete="SET NULL"), nullable=True)
    finding_type: Mapped[str] = mapped_column(String(100), nullable=False)
    source_link: Mapped[str | None] = mapped_column(String(512), nullable=True)
    source_header: Mapped[str | None] = mapped_column(String(255), nullable=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    confidence_score: Mapped[Decimal | None] = mapped_column(DECIMAL(3, 2), nullable=True)
    relevancy_score: Mapped[Decimal | None] = mapped_column(DECIMAL(3, 2), nullable=True)
    raw_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    is_selected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # New fields for pain points with source tracking
    source_type: Mapped[str | None] = mapped_column(String(50), nullable=True)  # "internet" | "uploaded_material" | "research_agent"
    source_reference: Mapped[str | None] = mapped_column(String(512), nullable=True)  # URL, material ID, or reference
    details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # Additional metadata

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
