You are building the GovFlow FastAPI backend with all routes, auth, and WebSocket. Follow docs/implementation/03-backend-api.md as the detailed guide.

Task: $ARGUMENTS (default: full API)

## What You Build

Complete FastAPI application with JWT auth, all API routes, WebSocket manager, and Pydantic schemas.

## Steps

1. **`backend/src/main.py`** — FastAPI app factory:
   - Lifespan: connect GDB pool, Hologres pool, OSS client on startup; close on shutdown
   - Include all routers with prefix /api
   - CORS middleware for frontend origin (localhost:3000)
   - Slowapi rate limiting
   - Error handler middleware (structured JSON errors)

2. **`backend/src/auth.py`** — JWT authentication:
   - python-jose HS256 with JWT_SECRET from config
   - Claims: sub, clearance_level (Unclassified|Confidential|Secret|Top Secret), departments[], role (citizen|staff|supervisor|leader|security|admin)
   - `get_current_user` dependency for protected routes
   - Mock login endpoint: POST /api/auth/login (username+password -> JWT)

3. **API Routes** (each in `backend/src/api/`):
   ```
   cases.py:
     POST /api/cases              — Create case from bundle metadata
     GET  /api/cases/{id}         — Get case with permission masking
     POST /api/cases/{id}/bundles — Add supplementary documents
     POST /api/cases/{id}/finalize — Bundle upload complete, trigger pipeline
     GET  /api/cases/{id}/timeline — Case timeline events

   documents.py:
     GET /api/documents/{id}           — Document metadata + entities
     GET /api/documents/{id}/signed-url — OSS presigned download URL

   agents.py:
     GET  /api/agents/trace/{case_id} — Agent trace (AgentStep vertices)
     POST /api/agents/run/{case_id}   — Trigger agent pipeline

   graph.py:
     POST /api/graph/query            — Ad-hoc Gremlin (admin only)
     GET  /api/graph/case/{id}/subgraph — Case context graph for visualization

   search.py:
     GET /api/search/law?q=...  — Vector search law_chunks
     GET /api/search/tthc?q=... — Search TTHC catalog

   leadership.py:
     GET /api/leadership/dashboard — SLA metrics, case stats
     GET /api/leadership/inbox     — Cases pending approval

   audit.py:
     GET /api/audit/events — Query audit log with filters

   notifications.py:
     GET   /api/notifications          — User notifications
     PATCH /api/notifications/{id}/read — Mark as read

   public.py:
     GET /api/public/cases/{code} — Citizen case tracking (no auth)
     GET /api/public/tthc         — Browse TTHC catalog (no auth)
     GET /api/public/stats        — Public statistics (no auth)
   ```

4. **`backend/src/api/ws.py`** — WebSocket manager:
   - Endpoint: /api/ws?token=JWT
   - Topic-based pub/sub: case:{id}, dept:{id}:inbox, user:{id}:notifications, security:audit
   - ConnectionManager class with subscribe/unsubscribe/broadcast methods
   - JWT auth on WebSocket connect

5. **`backend/src/api/schemas.py`** — Pydantic v2 models:
   - CaseCreate, CaseResponse, CaseTimeline
   - DocumentResponse, UploadURLResponse
   - AgentTraceEvent, AgentStepResponse
   - GraphSubgraph (nodes + edges for React Flow)
   - DashboardMetrics, InboxItem
   - AuditEventResponse, NotificationResponse

## Conventions
- All handlers async
- Use Depends() for auth and database injection
- Proper HTTP status codes (201 for create, 404 for not found, 403 for forbidden)
- Structured error responses: {"detail": "message", "code": "ERROR_CODE"}
- Vietnamese descriptions in OpenAPI schema for demo

## Spec References
- docs/03-architecture/overview.md — System layers and request flow
- docs/04-ux/realtime-interactions.md — WebSocket event types

## Verification
```bash
cd backend && .venv/bin/uvicorn src.main:app --reload --port 8000
curl http://localhost:8000/api/docs  # OpenAPI UI
curl -X POST http://localhost:8000/api/auth/login -d '{"username":"admin","password":"admin"}'
curl http://localhost:8000/api/public/tthc  # Returns 5 TTHCs
# WebSocket test with wscat or Python websockets
```