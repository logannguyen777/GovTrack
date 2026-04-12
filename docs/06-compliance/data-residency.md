# Data Residency — Chiến lược on-prem

## The problem

Vietnamese gov data has strict residency requirements:
- **Luật ANM 2018 Điều 26:** dữ liệu cá nhân công dân VN phải lưu trữ tại VN
- **NĐ 53/2022 Điều 26:** enumerated categories that must stay in VN
- **Luật BVBMNN 2018:** dữ liệu mật nhà nước không được rời hạ tầng kiểm soát

**Consequence:** Cannot use ChatGPT, Claude, Gemini directly — they're US-based SaaS with data going to US servers.

**This is the #1 reason why Vietnamese gov is behind in LLM adoption:** chưa có giải pháp LLM mạnh vừa chạy on-prem vừa support tiếng Việt tốt.

## GovFlow solution — 3 deployment modes

### Mode A — Hackathon demo (current)
- Alibaba Cloud Singapore region (closest to VN)
- Qwen via Model Studio (data goes to Alibaba Cloud Singapore, not US)
- Singapore region acceptable for PoC of non-sensitive data
- Fast iteration + low cost

### Mode B — PoC with 1 Sở (3-month timeline)
- **Still Alibaba Cloud Singapore** but with:
  - DPA (Data Processing Agreement) with Alibaba Cloud Vietnam
  - Data residency addendum
  - Audit logging enabled
  - Encrypted at rest + in transit
- For **non-classified TTHC data** (most public TTHCs like CPXD, ĐKKD are ultimately public records)
- Still dùng Model Studio hosted Qwen
- This is the fastest PoC path

### Mode C — Production for classified / sensitive gov
- **Deploy on customer on-prem hardware**
- Use **Qwen3 open-weight** (Apache 2.0 license) deployed via **PAI-EAS** or directly on customer GPU
- GovFlow backend deployed on-prem alongside LLM
- Alibaba Cloud GDB replaced with **self-hosted graph DB** (JanusGraph/Neo4j on customer infra)
- Hologres replaced with **self-hosted Postgres + pgvector**
- OSS replaced with **self-hosted MinIO**

This mode achieves: **full data residency + strong LLM capability** — the unique selling point no other team/product has.

## Why Qwen3 open-weight is the magic

| LLM | Open weights | License | Size | VN language |
|---|---|---|---|---|
| GPT-4 | No | Closed | N/A | Good |
| Claude 3 | No | Closed | N/A | OK |
| Gemini Pro | No | Closed | N/A | Good |
| **Qwen3** | **Yes** | **Apache 2.0** | 7B / 32B / 235B | **Excellent (trained on 119 langs)** |
| Llama 3 | Yes | Custom (restrictive) | 8B / 70B | OK |

**Qwen3 open-weight + Apache 2.0 = customer can legally deploy on-prem for gov use.**

This is a massive deal for Vietnamese public sector. And it's why Alibaba Cloud Qwen AI Build Day is hosting this challenge.

## Pitch talking point

> "Tại sao FPT/Viettel/VNPT không làm được giải pháp LLM-powered này cho gov? Vì họ phụ thuộc vào OpenAI/Google — gov không dùng được do Luật ANM + NĐ 53/2022. Qwen3 open-weight Apache 2.0 là lời giải duy nhất — vừa mạnh ngang GPT-4, vừa có thể deploy on-prem tuân thủ luật VN. GovFlow tận dụng điểm này: demo chạy cloud cho speed, PoC chạy Singapore cho cost, production chạy on-prem cho compliance. Đó là lý do Alibaba Cloud + Shinhan đang tìm startup như chúng em."

## Technical implementation — Mode C deep dive

### On-prem deployment architecture

```
┌─────────────────────────────────────────────────────┐
│    Customer Data Center (Vietnam)                    │
│                                                       │
│    ┌────────────────────────────────────────────┐   │
│    │ Application Layer                           │   │
│    │                                              │   │
│    │  Next.js frontend  ──  FastAPI backend      │   │
│    └────────────────────────────────────────────┘   │
│                         │                             │
│    ┌────────────────────▼───────────────────────┐   │
│    │ Data Layer                                  │   │
│    │                                              │   │
│    │  Neo4j (KG + CG)                             │   │
│    │  Postgres + pgvector (relational + vector)  │   │
│    │  MinIO (S3-compatible blobs)                 │   │
│    └────────────────────┬───────────────────────┘   │
│                         │                             │
│    ┌────────────────────▼───────────────────────┐   │
│    │ AI Layer                                    │   │
│    │                                              │   │
│    │  Qwen3-32B open weight                      │   │
│    │  Deployed via vLLM or TGI                   │   │
│    │  GPU: 2x A100 80GB or 4x H100 (for scale)   │   │
│    │  Qwen3-VL for multimodal                    │   │
│    └────────────────────────────────────────────┘   │
│                                                       │
│    All traffic stays within customer VPC / DC         │
└─────────────────────────────────────────────────────┘

           No external egress except:
           - Gov-approved APIs (VNeID, Cổng DVC)
           - Email/SMS gateway
           - CDN (frontend static assets only)
```

### Qwen3 on-prem inference

Using vLLM:
```bash
vllm serve Qwen/Qwen3-32B-Instruct \
    --port 8000 \
    --tensor-parallel-size 2 \
    --max-model-len 32768 \
    --api-key local-secret
```

GovFlow agents connect to `http://localhost:8000` instead of Model Studio endpoint. Same OpenAI-compatible API, same code.

### Hardware recommendation for production on-prem

| Scale | GPU | CPU | RAM | Storage | Cost estimate |
|---|---|---|---|---|---|
| PoC 1 Sở (10k cases/year) | 1x A100 80GB | 32 cores | 256GB | 2TB NVMe | ~300M VND initial |
| 1 Sở production | 2x A100 80GB | 64 cores | 512GB | 5TB NVMe | ~600M VND initial |
| 5 Sở | 4x A100 or 2x H100 | 128 cores | 1TB | 10TB | ~1.2B VND |
| Tỉnh-level (all Sở) | 8x H100 | 256 cores | 2TB | 20TB | ~3B VND |

Alternatively, rent GPUs on Alibaba Cloud on-demand via PAI-EAS for elastic scaling — no upfront hardware cost.

### Storage strategy

- **Hot data (last 30 days active cases):** SSD
- **Warm data (last 1 year):** HDD
- **Cold data (1+ year archived):** tape or cold cloud storage

Total storage per Sở/year: ~100GB for active + 500GB archived. Manageable.

## Migration path: Singapore → on-prem

For customer starting PoC on Singapore then moving on-prem:

1. **Day 0–90:** Singapore PoC
2. **Day 60:** Start on-prem hardware procurement (parallel)
3. **Day 90:** PoC review, decide to go production
4. **Day 90–120:** Deploy on-prem stack
5. **Day 120–150:** Data migration (Neo4j → self-hosted, etc.)
6. **Day 150:** Cutover — all traffic on on-prem

GovFlow architecture chosen specifically to enable this migration with minimal code changes.

## Cost comparison

| Mode | Monthly cost | Pros | Cons |
|---|---|---|---|
| A: Hackathon cloud | ~$100 | Fastest, cheapest | Demo only |
| B: Singapore PoC | ~$500 | Fast, compliant for non-classified | Non-compliant for classified |
| C: On-prem production | ~$10–50k/year (amortized) | Full compliance | Higher upfront + ops burden |

Value: customer saves 100× compared to internal build or 10× compared to alternative vendors.

## Links

- Qwen3 HuggingFace: https://huggingface.co/Qwen
- Qwen3 GitHub: https://github.com/QwenLM/Qwen3
- vLLM for serving: https://github.com/vllm-project/vllm
- Alibaba Cloud PAI-EAS: https://www.alibabacloud.com/product/machine-learning
