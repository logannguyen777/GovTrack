You are adding a "Điền mẫu (demo)" quick-fill button to one specific GovFlow page.

## Argument
$ARGUMENTS — target page: `intake` | `dashboard` | `compliance` | `inbox` | `security` | path

## Workflow

1. Resolve target file:
   - `intake` → `frontend/src/app/(internal)/intake/page.tsx`
   - `dashboard` → `frontend/src/app/(internal)/dashboard/page.tsx`
   - `compliance` → `frontend/src/app/(internal)/compliance/[case_id]/page.tsx`
   - `inbox` → `frontend/src/app/(internal)/inbox/page.tsx`
   - `security` → `frontend/src/app/(internal)/security/page.tsx`
   - custom path → use as-is

2. Invoke `ux-polish-agent` via Task tool with the target file + the instruction: "Add Điền mẫu (demo) quick-fill button following submit-wizard.tsx:265-278 pattern. Wire to the matching demo endpoint in backend/src/api/demo.py or public.py — check there first."

3. After agent returns, run:
```bash
cd /home/logan/GovTrack/frontend && npx tsc --noEmit
```

4. If green, summarize file:line changes and show the added button snippet.

## Fallback

If no demo endpoint exists for the page, agent should add one inline via mock data in the component itself (acceptable for hackathon demo) and flag to user that a proper backend endpoint is preferable.