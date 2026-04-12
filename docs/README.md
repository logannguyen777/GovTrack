# GovFlow — Qwen AI Build Day 2026 (Public Sector Track)

> **Agentic GraphRAG for Vietnam Public Administrative Services**
>
> Graph-native multi-agent system trên Qwen3 + Alibaba Cloud GDB/Hologres, xử lý end-to-end vòng đời TTHC công Việt Nam từ công dân nộp hồ sơ đến nhận kết quả.

---

## Đọc tài liệu này thế nào

Tài liệu được viết **trước khi code**. Mục tiêu: cả team hiểu rõ **problem → solution → mindset → theme** trước khi build, để khi vào code không ai phải đoán.

Đọc theo thứ tự:

1. **[00-context/](00-context/)** — nắm hackathon + đề bài gốc + cách mình hiểu scope.
2. **[01-problem/](01-problem/)** — painpoint sâu của 6 nhóm stakeholder TTHC Việt Nam, quy mô, regulatory landscape, ví dụ 5 TTHC thật.
3. **[02-solution/](02-solution/)** — vision, nguyên tắc, theme, coverage matrix (solution vs PDF), khác biệt so với đối thủ.
4. **[03-architecture/](03-architecture/)** — dual graph + 10 agent + 3-tier permission + Agentic GraphRAG + Alibaba Cloud stack.
5. **[04-ux/](04-ux/)** — design system, 8 màn hình, user journey, graph visualization, realtime interaction.
6. **[05-business/](05-business/)** — TAM, GTM, pricing, unit economics, competitive landscape, Shinhan proposal.
7. **[06-compliance/](06-compliance/)** — legal framework mapping, security model, data residency, VNeID.
8. **[07-pitch/](07-pitch/)** — deck outline, demo video storyboard, Q&A prep, judge panel analysis.
9. **[08-execution/](08-execution/)** — daily plan 12–17/04, milestones, risks, verification rubric.
10. **[09-research/](09-research/)** — papers, Alibaba Cloud product docs, Qwen3 capabilities, field notes.

## Quick facts

- **Event:** Qwen AI Build Day 2026, TP.HCM, pitch 21/04
- **Track:** Public Sector (Government) — Document Intelligence
- **Prize:** USD 1,000 + up to 200M VND PoC funding qua Shinhan InnoBoost
- **Judges:** Alibaba Cloud SA, VC (GenAI Fund, Tasco CVC), operator (Elfie)
- **Tieu chi cham:** Problem Relevance + Solution Quality + Use of Qwen + Execution & Demo
- **Today:** 12/04/2026 — build day 2 / 6
- **Submission deadline:** 17/04/2026

## Big idea one-liner

*GovFlow là graph-native agentic system chạy trên Qwen3 + MCP, xây trên Knowledge Graph pháp luật Việt Nam + Context Graph động cho mỗi hồ sơ, với 10 agent có phân quyền tại mức node/edge. Biến toàn bộ vòng đời TTHC công từ hàng tuần/tháng xuống vài phút, bám đúng NĐ 61/2018, 107/2021, 45/2020, 30/2020, Đề án 06.*

## Strategy source of truth

Strategic plan gốc: [`/home/logan/.claude/plans/wise-hugging-shell.md`](/home/logan/.claude/plans/wise-hugging-shell.md). Docs này là expansion chi tiết.
