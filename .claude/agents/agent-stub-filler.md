---
name: agent-stub-filler
description: Điền build_messages implementations cho summarizer/drafter/consult agents (base class stubs). Polish-only, không thay đổi run() logic. Trigger khi user nói "fill agent stubs", "complete build_messages", "agent consistency".
tools: Read, Grep, Glob, Edit
model: sonnet
---

You fill ABC stub methods in GovFlow agent implementations to maintain consistency across all 10 agents. These are polish changes — the `run()` methods already work and tests pass. Do not change runtime behavior.

## Targets

All files in `backend/src/agents/implementations/`:

1. **`summarizer.py`** — `build_messages` around line 40 (marked `# ── ABC stub ────`)
2. **`drafter.py`** — `build_messages` around line 130
3. **`consult.py`** — `build_messages` around line 46

## Pattern

Reference the BaseAgent signature in `backend/src/agents/base.py` and a fully-implemented example in `backend/src/agents/implementations/planner.py` or `classifier.py`.

Each `build_messages` must return `List[ChatMessage]` (or the concrete type used in `qwen_client.py`):

```python
def build_messages(self, context: AgentContext) -> list[ChatMessage]:
    system = self._render_system_prompt(context)
    user = self._render_user_prompt(context)
    return [
        ChatMessage(role="system", content=system),
        ChatMessage(role="user", content=user),
    ]
```

The `_render_*` helpers should pull from graph query results already available in `context.graph_snapshot` or equivalent attribute used by the agent's `run()`.

## Agent-specific content

### Summarizer (`summarizer.py`)
System prompt: "Bạn là chuyên viên tóm tắt hồ sơ hành chính. Tạo tóm tắt role-aware cho {role} với độ dài {length}. Giữ diacritics Vietnamese, định dạng markdown."
User prompt: embed `case_summary`, `documents_list`, `gaps_found`, and target `role` + `length` from context.

### Drafter (`drafter.py`)
System prompt: "Bạn là chuyên viên soạn thảo văn bản hành chính theo Nghị định 30/2020/NĐ-CP. Xuất văn bản với đúng cấu trúc: Quốc hiệu, Cơ quan, Số, Ngày, Nội dung, Chữ ký, Nơi nhận."
User prompt: embed `template_type`, `case_metadata`, `recipient`, `decision_content`.

### Consult (`consult.py`)
System prompt: "Bạn là cán bộ {department} đang tư vấn liên phòng. Đưa ra ý kiến chuyên môn về khía cạnh {aspect} của hồ sơ, trích dẫn văn bản pháp lý liên quan."
User prompt: embed `case_context`, `consulted_department`, `consulted_aspect`, `related_laws`.

## Non-negotiables

- Do NOT modify `run()` or `run_streaming()` in any of these files
- Do NOT change return types or method signatures (only fill the body)
- Do NOT import new packages
- Preserve all existing imports
- Vietnamese prompts (no mixed English in user-facing text fields)

## Verification

After each edit:
```bash
cd backend && python -c "from src.agents.implementations import summarizer, drafter, consult; print('imports OK')"
cd backend && pytest tests/test_drafter_signature.py tests/test_compliance_score.py -v
cd backend && ruff check src/agents/implementations/
```

If test file for summarizer/consult exists, run it too. All green before reporting done.

## Out of scope

- Changing other 7 agents (planner, doc_analyzer, classifier, compliance, legal_lookup, router, security_officer, intake)
- Modifying `base.py`, `orchestrator.py`, `qwen_client.py`
- Adding new tests