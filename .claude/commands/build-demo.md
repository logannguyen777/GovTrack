You are preparing GovFlow's demo environment. Follow docs/implementation/19-demo-preparation.md as the detailed guide.

Task: $ARGUMENTS (default: full demo preparation)

## What You Build

Seed data, demo scenario scripts, Qwen response cache, reset/start scripts, and backup plans.

## Steps

### 1. Seed Data (`scripts/seed_demo.py`)

**5 demo users:**
- Anh Minh: citizen, Unclassified clearance
- Chi Lan: staff intake officer, Confidential clearance
- Anh Tuan: staff processor, Confidential clearance
- Chi Huong: department leader, Secret clearance
- Anh Dung: legal advisor, Confidential clearance
- Anh Quoc: CIO/security, Top Secret clearance

**5 pre-processed cases** (1 per TTHC at different stages):
- CPXD (1.004415): "gap found" state — hero demo path, missing PCCC
- GCN QSDD (1.000046): "routing" state
- DKKD (1.001757): completed + published
- LLTP (1.000122): "compliance check" state
- GPMT (2.002154): "consult" state

**Additional data:**
- 3 completed cases for Leadership Dashboard metrics
- 25 test cases for benchmark display
- Sample documents in OSS for each case

### 2. Demo Scenario Scripts (`scripts/demo/`)

```
scenario_1_cpxd_gap.py    — Full CPXD flow: submit -> agents process -> PCCC gap detected -> citizen notified
scenario_2_permission.py  — 3 permission scenes: SDK Guard, RBAC, Property Mask elevation
scenario_3_trace.py       — Real-time agent trace viewer with graph growing
scenario_4_leadership.py  — Dashboard with SLA metrics + Hologres AI Functions brief
scenario_5_elevation.py   — Clearance elevation with blur-to-clear animation
```

Each script: set up state -> trigger action -> verify result -> print success.

### 3. Cache Warming (`scripts/warm_cache.py`)

- Pre-run all 5 demo cases through agent pipeline
- Cache Qwen3 responses: key = hash(model, messages, tools)
- Store cache in Redis or local JSON file
- `DEMO_MODE=true` env var -> check cache before API call

### 4. Environment Scripts

```bash
# scripts/demo/reset_demo.sh — Reset all data to initial seed state (idempotent)
# scripts/demo/start_demo.sh — Start all services in demo mode
```

### 5. Demo Hardening
- Pin all API versions (Qwen model versions)
- Disable rate limiting for demo user
- Increase Qwen call timeout to 60s
- Pre-load all frontend routes in browser cache

### 6. Backup Plan
- Record 2:30 demo video (per docs/07-pitch/demo-video-storyboard.md)
- Create 10-slide screenshot deck as secondary backup
- Copy everything to USB drive
- Local cache mode: all API calls resolve from cache, no network needed

## Spec References
- docs/07-pitch/demo-video-storyboard.md — Video scene structure
- docs/08-execution/verification-rubric.md — Demo stress test gates

## Verification
```bash
# Reset and seed
bash scripts/demo/reset_demo.sh
python scripts/seed_demo.py

# Run each scenario
python scripts/demo/scenario_1_cpxd_gap.py    # Should complete in < 90s
python scripts/demo/scenario_2_permission.py   # 3 scenes pass
python scripts/demo/scenario_3_trace.py        # Agent trace visible

# Cache mode works
DEMO_MODE=true python scripts/demo/scenario_1_cpxd_gap.py  # Should complete in < 5s

# Demo reliability: run 3x back-to-back
for i in 1 2 3; do python scripts/demo/scenario_1_cpxd_gap.py; done
```