import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str | None = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# =========================================
# Research Schemas
# =========================================

class PlanStepOut(BaseModel):
    id: uuid.UUID
    step_order: int
    agent_type: str
    description: str
    status: str
    result: dict | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class FindingOut(BaseModel):
    id: uuid.UUID
    finding_type: str
    source_link: str | None
    source_header: str | None
    summary: str
    confidence_score: float | None
    relevancy_score: float | None
    is_selected: bool
    source_type: str | None
    source_reference: str | None
    details: dict | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ResearchSessionCreate(BaseModel):
    prospect_input: str = Field(min_length=1)


class ResearchSessionOut(BaseModel):
    id: uuid.UUID
    prospect_input: str
    prospect_name: str | None = None
    prospect_company: str | None = None
    prospect_title: str | None = None
    research_summary: str | None = None
    status: str
    plan: list = []
    findings: list = []
    methodology: str | None
    generated_output: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class GenerateScriptRequest(BaseModel):
    methodology: str
    finding_ids: list[uuid.UUID] = []


class UserSettingsOut(BaseModel):
    deepseek_api_key: str | None
    deepseek_endpoint: str | None
    newsapi_endpoint: str | None
    product_name: str | None
    default_framework: str

    model_config = {"from_attributes": True}


class UserSettingsUpdate(BaseModel):
    deepseek_api_key: str | None = None
    deepseek_endpoint: str | None = None
    newsapi_endpoint: str | None = None
    product_name: str | None = None
    default_framework: str | None = None


# =========================================
# Company Materials Schemas
# =========================================

class CompanyMaterialOut(BaseModel):
    id: uuid.UUID
    material_type: str
    name: str
    file_size: int
    mime_type: str
    description: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class CompanyMaterialCreate(BaseModel):
    material_type: str = Field(pattern="^(brochure|sales_script|product_info|custom)$")
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None


class PainPointOut(BaseModel):
    title: str
    description: str
    source: str  # "internet" | "uploaded_material"
    source_reference: str | None  # URL or material ID
    confidence: float  # 0.0 to 1.0
    details: dict | None  # additional metadata
