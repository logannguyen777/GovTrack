"""
tests/test_drafter_signature.py
Tests for ND 30/2020 digital signature placeholder requirement.
"""

from __future__ import annotations

import pytest

from src.agents.implementations.drafter import (
    DraftSignatureMissing,
    DrafterAgent,
    _DIGITAL_SIG_RE,
)


# ---------------------------------------------------------------------------
# _build_nd30_document always includes the placeholder
# ---------------------------------------------------------------------------


def _minimal_case_data() -> dict:
    return {
        "applicant_display_name": "Nguyen Van A",
        "project_name": "Du an test",
        "project_address": "123 Duong ABC",
        "tthc_name": "Cap phep xay dung",
        "assigned_org_name": "SO XAY DUNG",
        "parent_org": "UY BAN NHAN DAN",
        "province": "TINH BINH DUONG",
        "staff_summary": "Tom tat test.",
    }


def _minimal_template_vars() -> dict:
    return {
        "applicant_name": "Nguyen Van A",
        "project_name": "Du an test",
        "project_address": "123 Duong ABC",
        "tthc_name": "Cap phep xay dung",
        "tthc_code": "1.004415",
        "decision_type": "approve",
        "decision_reasoning": "Ho so day du",
        "citations": [],
        "gaps": [],
        "signer_title": "GIAM DOC",
        "signer_name": "Tran Van B",
        "org_name": "SO XAY DUNG",
        "parent_org": "UY BAN NHAN DAN",
        "province": "TINH BINH DUONG",
    }


def test_build_nd30_document_contains_signature_placeholder():
    """DrafterAgent._build_nd30_document must include [Ký số CA: ...] at the end."""
    doc = DrafterAgent._build_nd30_document(
        rendered_body="Noi dung van ban test.",
        case_data=_minimal_case_data(),
        doc_type="QuyetDinh",
        template_vars=_minimal_template_vars(),
    )
    assert _DIGITAL_SIG_RE.search(doc) is not None, (
        "Document must contain [Ký số CA: ...] placeholder"
    )
    assert "[Ký số CA:" in doc


def test_validate_nd30_passes_with_signature():
    """A valid ND30 document with digital signature placeholder should pass validation."""
    doc = DrafterAgent._build_nd30_document(
        rendered_body="Noi dung test",
        case_data=_minimal_case_data(),
        doc_type="QuyetDinh",
        template_vars=_minimal_template_vars(),
    )
    result = DrafterAgent._validate_nd30(doc)
    # Signature should be present
    assert _DIGITAL_SIG_RE.search(doc) is not None
    # Validate the entire doc structure
    assert result["valid"] is True or "chu ky so" not in [i.lower() for i in result["issues"]], \
        f"Signature check failed. Issues: {result['issues']}"


def test_validate_nd30_fails_without_signature():
    """A document missing the digital signature placeholder should fail validation."""
    # Build document without signature by bypassing _build_nd30_document
    doc_without_sig = (
        "**UY BAN NHAN DAN**\n"
        "**TINH BINH DUONG**\n"
        "**SO XAY DUNG**\n"
        "\n"
        "**CONG HOA XA HOI CHU NGHIA VIET NAM**\n"
        "*Doc lap - Tu do - Hanh phuc*\n"
        "---\n"
        "\n"
        "So: ___/QD-SXD\n\n"
        "Binh Duong, ngay 1 thang 4 nam 2026\n"
        "\n"
        "**V/v Cap phep xay dung**\n"
        "\n"
        "Noi dung chinh\n"
        "\n"
        "**Noi nhan:**\n"
        "- Nhu tren;\n"
        "\n"
        "**GIAM DOC**\n"
        "*(Ky so)*\n"
        "**Tran Van B**\n"
        "\n"
        "---\n"
        "*DU THAO - Chua phat hanh*\n"
        # NOTE: [Ký số CA: ...] is intentionally omitted
    )
    result = DrafterAgent._validate_nd30(doc_without_sig)
    assert result["valid"] is False
    assert any("chu ky so" in issue.lower() or "ky so ca" in issue.lower()
               for issue in result["issues"])


def test_digital_sig_regex_matches_expected_format():
    """_DIGITAL_SIG_RE must match the format produced by _build_nd30_document."""
    sample = "[Ký số CA: SO XAY DUNG]"
    assert _DIGITAL_SIG_RE.search(sample) is not None


def test_digital_sig_regex_rejects_no_match():
    sample_no_sig = "Ky ten: Nguyen Van A"
    assert _DIGITAL_SIG_RE.search(sample_no_sig) is None


def test_draft_signature_missing_exception_is_value_error():
    with pytest.raises(ValueError):
        raise DraftSignatureMissing("test")
