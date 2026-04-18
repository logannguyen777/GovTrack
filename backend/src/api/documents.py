"""backend/src/api/documents.py"""

import ipaddress
import logging
import re
import socket
import uuid
import zipfile
from io import BytesIO
from urllib.parse import urlparse

import magic
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import Response

from ..auth import CurrentUser
from ..config import settings
from ..database import get_oss_client, oss_get_signed_url, oss_put_object
from ..graph.deps import PermittedGDBDep
from ..graph.permitted_client import PermittedGremlinClient
from ..models.chat_schemas import ExtractResponse
from ..models.schemas import DocumentResponse

logger = logging.getLogger("govflow.documents")
router = APIRouter(prefix="/documents", tags=["Documents"])

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_ALLOWED_EXTENSIONS = {"pdf", "docx", "xlsx", "png", "jpg", "jpeg"}

_ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "image/png",
    "image/jpeg",
}

_ZIP_BASED_MIME = {
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}

# Regex for safe filenames: alnum, underscore, hyphen, period; max 200 chars
_SAFE_FILENAME_RE = re.compile(r"^[a-zA-Z0-9_\-. ]{1,200}$")

# Explicit metadata IP to block (defence-in-depth)
_METADATA_IP = ipaddress.ip_address("169.254.169.254")


# ---------------------------------------------------------------------------
# SSRF validation helper
# ---------------------------------------------------------------------------


def _is_private_ip(addr_str: str) -> bool:
    """Return True if the IP address is private, loopback, link-local, or multicast."""
    try:
        addr = ipaddress.ip_address(addr_str)
    except ValueError:
        return True  # Unparseable — treat as unsafe
    if addr == _METADATA_IP:
        return True
    return (
        addr.is_private
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_multicast
        or addr.is_reserved
        or addr.is_unspecified
    )


async def _validate_url(url: str) -> None:
    """SSRF guard: validate a URL before passing to any external service.

    Checks:
    - HTTPS required in cloud mode (HTTP allowed only in local mode for MinIO).
    - Hostname must resolve to at least one non-private IP.
    - 169.254.169.254 (IMDS) explicitly rejected.
    - Hostname must be in the OSS allowed-domain list.
    """
    parsed = urlparse(url)
    scheme = (parsed.scheme or "").lower()

    # Scheme check
    if settings.govflow_env == "cloud" and scheme != "https":
        raise HTTPException(
            status_code=400,
            detail="Chỉ chấp nhận URL HTTPS trong môi trường cloud.",
        )
    if scheme not in ("http", "https"):
        raise HTTPException(
            status_code=400,
            detail="URL không hợp lệ: chỉ hỗ trợ HTTP/HTTPS.",
        )

    netloc = parsed.netloc or ""
    hostname = netloc.split(":")[0].lower()

    if not hostname:
        raise HTTPException(status_code=400, detail="URL thiếu hostname.")

    # OSS domain allowlist
    allowed = settings.oss_allowed_domains
    if not any(d in netloc for d in allowed):
        raise HTTPException(
            status_code=400,
            detail="URL không được phép. Chỉ chấp nhận URL từ OSS của hệ thống.",
        )

    # Resolve hostname and check all returned IPs
    try:
        infos = await _resolve_hostname(hostname)
    except socket.gaierror:
        raise HTTPException(status_code=400, detail="Không thể phân giải hostname.")

    for addr_str in infos:
        if _is_private_ip(addr_str):
            raise HTTPException(
                status_code=400,
                detail="URL trỏ đến địa chỉ IP nội bộ — bị từ chối.",
            )


async def _resolve_hostname(hostname: str) -> list[str]:
    """Resolve hostname to all A/AAAA addresses (async-safe via executor)."""
    import asyncio

    loop = asyncio.get_event_loop()
    results = await loop.run_in_executor(
        None,
        lambda: socket.getaddrinfo(hostname, None, 0, socket.SOCK_STREAM),
    )
    return [info[4][0] for info in results]


# ---------------------------------------------------------------------------
# Filename sanitisation
# ---------------------------------------------------------------------------


def _sanitize_filename(filename: str) -> str:
    """Strip path separators, ``..``, and unsafe chars; truncate to 200 chars.

    Returns a safe filename or raises HTTPException 400 if nothing usable remains.
    """
    # Remove directory separators and null bytes
    name = filename.replace("/", "").replace("\\", "").replace("\x00", "")
    # Strip leading dots (hidden files / path traversal)
    name = name.lstrip(".")
    # Keep only alnum, underscore, hyphen, period, space
    name = re.sub(r"[^a-zA-Z0-9_\-. ]", "_", name)
    name = name[:200].strip()
    if not name:
        raise HTTPException(status_code=400, detail="Tên tệp không hợp lệ.")
    return name


# ---------------------------------------------------------------------------
# ZIP slip guard
# ---------------------------------------------------------------------------


def _check_zip_slip(data: bytes) -> None:
    """Scan ZIP entry names for path traversal (ZIP slip attack)."""
    try:
        with zipfile.ZipFile(BytesIO(data)) as zf:
            for entry in zf.namelist():
                if ".." in entry or entry.startswith("/") or entry.startswith("\\"):
                    raise HTTPException(
                        status_code=400,
                        detail="Tệp chứa đường dẫn nguy hiểm (ZIP slip).",
                    )
    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="Tệp ZIP không hợp lệ.")


# ---------------------------------------------------------------------------
# GDB helpers
# ---------------------------------------------------------------------------


async def _find_document(doc_id: str, gdb: PermittedGremlinClient) -> dict | None:
    """Look up a Document vertex by ``doc_id``/``document_id`` property,
    falling back to the raw GDB vertex id if the caller passed a numeric id.

    Legacy seeds used ``document_id``; newer writes use ``doc_id``; the
    subgraph endpoint hands out raw vertex ids. Support all three so UI
    callers (which may not have the domain id to hand) don't 404.
    """
    for prop in ("doc_id", "document_id"):
        result = await gdb.execute(
            f"g.V().has('Document', '{prop}', did).valueMap(true)",
            {"did": doc_id},
        )
        if result:
            return result[0]
    # Final fallback: numeric vertex id. "id" is reserved as a binding name
    # on the Gremlin server, so use a different parameter name.
    if doc_id.isdigit():
        try:
            result = await gdb.execute(
                "g.V(vid).hasLabel('Document').valueMap(true)",
                {"vid": int(doc_id)},
            )
            if result:
                return result[0]
        except Exception:
            pass
    return None


# ---------------------------------------------------------------------------
# Route handlers
# ---------------------------------------------------------------------------


@router.get("/{doc_id}", response_model=DocumentResponse)
async def get_document(doc_id: str, user: CurrentUser, gdb: PermittedGDBDep):
    """Get document metadata."""
    props = await _find_document(doc_id, gdb)
    if not props:
        raise HTTPException(status_code=404, detail="Document not found")

    def _g(p: dict, key: str, default=None):
        v = p.get(key, [default] if default is not None else [None])
        val = v[0] if isinstance(v, list) else v
        # Treat empty string as None so optional typed fields don't fail
        # pydantic int/float parsing.
        return None if val == "" else val

    raw_page_count = _g(props, "page_count")
    try:
        page_count_int = int(raw_page_count) if raw_page_count is not None else None
    except (ValueError, TypeError):
        page_count_int = None

    return DocumentResponse(
        doc_id=doc_id,
        filename=_g(props, "filename") or "",
        content_type=_g(props, "content_type") or "",
        page_count=page_count_int,
        ocr_status=_g(props, "ocr_status") or "pending",
        oss_key=_g(props, "oss_key") or "",
    )


@router.get("/{doc_id}/view")
async def view_document(doc_id: str, token: str | None = None):
    """Proxy-stream a document from OSS with ``Content-Disposition: inline``.

    Alibaba OSS accounts may have ``x-oss-force-download: true`` set at the
    service level, which causes browsers to download PDFs/images instead of
    rendering them in an ``<iframe>`` or ``<img>``. This endpoint side-steps
    that by streaming the object through the backend with inline headers.

    Accepts JWT via ``?token=...`` query string because ``<iframe src=...>``
    and ``<img src=...>`` cannot send Authorization headers.
    """
    if not token:
        raise HTTPException(status_code=401, detail="token required")
    try:
        from ..auth import decode_token
        decode_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="invalid token")

    # Use raw gremlin (no permission client) — we've already validated the token.
    from ..database import async_gremlin_submit

    props = None
    for prop in ("doc_id", "document_id"):
        rows = await async_gremlin_submit(
            f"g.V().has('Document', '{prop}', did).valueMap(true)",
            {"did": doc_id},
        )
        if rows:
            props = rows[0]
            break

    if not props:
        raise HTTPException(status_code=404, detail="Document not found")

    def _pick(prop: str) -> str:
        v = props.get(prop, "")
        return v[0] if isinstance(v, list) else (v or "")

    oss_key = _pick("oss_key")
    if not oss_key:
        raise HTTPException(status_code=404, detail="Document has no OSS key")

    filename = _pick("filename") or oss_key.rsplit("/", 1)[-1]
    content_type = _pick("content_type")
    if not content_type:
        lower = filename.lower()
        if lower.endswith(".pdf"):
            content_type = "application/pdf"
        elif lower.endswith((".jpg", ".jpeg")):
            content_type = "image/jpeg"
        elif lower.endswith(".png"):
            content_type = "image/png"
        else:
            content_type = "application/octet-stream"

    client = get_oss_client()
    try:
        result = client.get_object(oss_key)
        data = result.read()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"OSS fetch failed: {e}")

    return Response(
        content=data,
        media_type=content_type,
        headers={
            "Content-Disposition": f'inline; filename="{filename}"',
            "Cache-Control": "private, max-age=600",
            "X-Doc-Id": doc_id,
        },
    )


@router.get("/{doc_id}/signed-url")
async def get_document_url(doc_id: str, user: CurrentUser, gdb: PermittedGDBDep):
    """Get a pre-signed download URL for a document."""
    props = await _find_document(doc_id, gdb)
    if not props:
        raise HTTPException(status_code=404, detail="Document not found")
    oss_key_v = props.get("oss_key", [""])
    oss_key = oss_key_v[0] if isinstance(oss_key_v, list) else oss_key_v
    if not oss_key:
        raise HTTPException(status_code=404, detail="Document has no OSS key")
    url = oss_get_signed_url(oss_key)
    return {"doc_id": doc_id, "signed_url": url, "expires_in": 3600}


@router.post("/extract", response_model=ExtractResponse)
async def extract_document(
    file: UploadFile | None = File(None),
    file_url: str | None = Form(None),
    tthc_code: str | None = Form(None),
):
    """
    Public document extraction endpoint.
    Accepts either a file upload OR a pre-signed OSS URL.
    Runs DocAnalyzer OCR + entity extraction without writing to GDB.
    Result cached 1h and retrievable via GET /assistant/prefill/{extraction_id}.
    """
    from ..agents.implementations.doc_analyzer import DocAnalyzerAgent
    from ..api.assistant import store_extraction

    if not file and not file_url:
        raise HTTPException(
            status_code=400,
            detail="Vui lòng cung cấp file hoặc URL tài liệu.",
        )

    target_url: str

    if file_url:
        # SSRF guard: full validation before passing URL to VL model
        await _validate_url(file_url)
        target_url = file_url

    else:
        # --- File upload path ---
        assert file is not None

        # Size cap: default for public endpoint (no auth context here)
        max_mb = settings.max_upload_mb_default

        # Read file data (size capped before full read)
        data = await file.read()

        # Size validation
        if len(data) > max_mb * 1024 * 1024:
            raise HTTPException(
                status_code=413,
                detail=f"Tệp quá lớn. Tối đa {max_mb}MB.",
            )

        # Extension whitelist
        original_name = file.filename or "upload.bin"
        ext = original_name.rsplit(".", 1)[-1].lower() if "." in original_name else ""
        if ext not in _ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=415,
                detail=(
                    f"Định dạng tệp '.{ext}' không được hỗ trợ. "
                    f"Chấp nhận: {', '.join(sorted(_ALLOWED_EXTENSIONS))}."
                ),
            )

        # MIME type check via magic (first 4 KB)
        detected_mime = magic.from_buffer(data[:4096], mime=True)
        if detected_mime not in _ALLOWED_MIME_TYPES:
            raise HTTPException(
                status_code=415,
                detail=(
                    f"Nội dung tệp không khớp với định dạng được phép (phát hiện: {detected_mime})."
                ),
            )

        # ZIP slip guard for docx/xlsx
        if detected_mime in _ZIP_BASED_MIME:
            _check_zip_slip(data)

        # PDF → PNG conversion (Qwen-VL does not accept PDF directly)
        if detected_mime == "application/pdf":
            try:
                from pdf2image import convert_from_bytes
                pages = convert_from_bytes(data, dpi=200, first_page=1, last_page=1, fmt="png")
                if not pages:
                    raise RuntimeError("pdf2image returned no pages")
                buf = BytesIO()
                pages[0].save(buf, format="PNG", optimize=True)
                data = buf.getvalue()
                detected_mime = "image/png"
                original_name = (original_name.rsplit(".", 1)[0] or "page") + ".png"
            except Exception as e:
                logger.warning("PDF→PNG conversion failed, will send PDF as-is: %s", e)

        # Sanitise filename
        safe_name = _sanitize_filename(original_name)
        oss_key = f"extractions/{uuid.uuid4()}/{safe_name}"

        try:
            content_type = detected_mime
            oss_put_object(oss_key, data, content_type)
            target_url = oss_get_signed_url(oss_key, expires=1800)
        except Exception as e:
            logger.error("OSS upload failed for extraction: %s", e)
            raise HTTPException(
                status_code=503,
                detail="Không thể lưu tệp lên hệ thống. Vui lòng thử lại.",
            )

    # Run extraction (no GDB writes)
    try:
        analyzer = DocAnalyzerAgent()
        result = await analyzer.extract_entities_public(target_url, tthc_code)
    except Exception as e:
        logger.error("Extraction failed: %s", e, exc_info=True)
        raise HTTPException(
            status_code=502,
            detail="Không thể phân tích tài liệu. Vui lòng thử lại.",
        )

    # Cache result for wizard prefill
    store_extraction(result.extraction_id, result)

    return result
