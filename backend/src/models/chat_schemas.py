"""
backend/src/models/chat_schemas.py
Pydantic v2 schemas for the citizen-facing AI assistant API.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ChatContext(BaseModel):
    type: Literal["case", "submit", "portal"] = "portal"
    ref: str | None = None


class AttachmentInput(BaseModel):
    name: str
    url: str
    mime_type: str | None = None


class ChatMessageInput(BaseModel):
    role: Literal["user", "assistant"] = "user"
    content: str


class ChatRequest(BaseModel):
    session_id: str | None = None
    message: str = Field(min_length=1, max_length=2000)
    context: ChatContext = Field(default_factory=ChatContext)
    attachments: list[AttachmentInput] = Field(default_factory=list, max_length=5)


class IntentRequest(BaseModel):
    text: str = Field(min_length=3, max_length=500)


class IntentResponse(BaseModel):
    primary_tthc_code: str | None
    primary_confidence: float
    explanation: str
    alternatives: list[dict]  # [{tthc_code, name, confidence}]


class ExtractRequest(BaseModel):
    file_url: str | None = None
    tthc_code: str | None = None  # hint to bias entity extraction


class ExtractedEntity(BaseModel):
    key: str
    value: Any
    confidence: float
    bbox: list[int] | None = None


class ExtractResponse(BaseModel):
    extraction_id: str
    document_type: str | None
    entities: list[ExtractedEntity]
    raw_text: str
    confidence: float


class PrecheckRequest(BaseModel):
    tthc_code: str
    form_data: dict = Field(default_factory=dict)
    uploaded_doc_urls: list[str] = Field(default_factory=list)


class PrecheckResponse(BaseModel):
    score: float
    gaps: list[str]
    missing_docs: list[str]
    suggestions: list[str]


class FormSuggestRequest(BaseModel):
    tthc_code: str
    partial_form: dict = Field(default_factory=dict)
    uploaded_doc_urls: list[str] = Field(default_factory=list)


class FormSuggestion(BaseModel):
    field: str
    value: str
    confidence: float
    source: str  # e.g. "Trích từ ảnh CCCD upload"


class FormSuggestResponse(BaseModel):
    suggestions: list[FormSuggestion]


class ValidateRequest(BaseModel):
    tthc_code: str
    form_snapshot: dict = Field(default_factory=dict)


class FieldIssue(BaseModel):
    field: str
    issue: str
    suggestion: str


class ValidateResponse(BaseModel):
    field_issues: list[FieldIssue]


class RecommendationResponse(BaseModel):
    decision: str
    reasoning: str
    citations: list[dict]
    confidence: float


class ExplainCaseResponse(BaseModel):
    explanation: str
    next_step: str | None


class FieldHelpResponse(BaseModel):
    explanation: str
    example_correct: str | None
    example_incorrect: str | None
    related_law: str | None


# ---------------------------------------------------------------------------
# Drafter preview (NĐ 30/2020 compliance)
# ---------------------------------------------------------------------------


class NghiDinh30Check(BaseModel):
    """One row in the NĐ 30/2020 compliance checklist."""
    rule: str        # e.g. "Quốc hiệu – Tiêu ngữ"
    status: bool     # pass/fail
    detail: str      # human note


class DraftPreviewResponse(BaseModel):
    """NĐ 30/2020 formatted official-document preview + compliance checklist."""
    doc_title: str
    doc_number: str
    issue_date: str
    content_html: str     # ready to inject into <div>, NĐ 30 template
    checklist: list[NghiDinh30Check]
    score: int            # 0-100, percent rules passed
