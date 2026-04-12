# Qwen3 Capabilities Summary

Quick reference for what Qwen3 can do + how GovFlow uses it.

## Qwen3 family overview

Released April 2025 + updates through 2026. Alibaba Cloud flagship LLM family.

### Model variants

| Model | Parameters | Context | Strength |
|---|---|---|---|
| Qwen3-0.6B | 0.6B | 32k | Edge / mobile |
| Qwen3-1.7B | 1.7B | 32k | Small tasks |
| Qwen3-4B | 4B | 32k | Light agents |
| Qwen3-8B | 8B | 128k | General purpose |
| Qwen3-14B | 14B | 128k | Advanced |
| **Qwen3-32B** | **32B** | **128k** | **Target for on-prem** |
| Qwen3-30B-A3B | 30B (3B active) | 128k | Sparse, efficient |
| **Qwen3-235B-A22B** | **235B (22B active)** | **128k** | **Flagship** |
| Qwen3-Max | proprietary | 30k | **Production API** |

### License

- **Dense models (0.6B–32B):** Apache 2.0 — free for commercial use, including on-prem
- **Sparse/flagship:** Apache 2.0
- **Qwen3-Max (hosted):** proprietary, pay-per-token via Model Studio

## Capabilities GovFlow relies on

### 1. Function calling / Tool use

Qwen3 supports OpenAI-compatible function calling:

```python
tools = [
    {
        "type": "function",
        "function": {
            "name": "graph_query_template",
            "description": "Execute a graph query template",
            "parameters": {...}
        }
    }
]

response = client.chat.completions.create(
    model="qwen-max-latest",
    messages=[...],
    tools=tools,
    tool_choice="auto"
)

# Model calls tool
if response.choices[0].message.tool_calls:
    for tc in response.choices[0].message.tool_calls:
        # Execute tool and return result
        ...
```

**GovFlow use:** every agent uses function calling to invoke graph tools + LLM reasoning loop.

### 2. Model Context Protocol (MCP)

Qwen3 added MCP support in 2025-2026 updates. Allows:
- Tool discovery
- Resource access
- Prompt templates

**GovFlow use:** expose graph queries + law lookups as MCP tools for agents.

### 3. Long context (up to 1M tokens for some models)

- Qwen3-VL: 256k native, 1M expandable
- Qwen3-Max: 30k (Model Studio hosted)
- Qwen3-32B: 128k

**GovFlow use:** process large legal documents + bundle of multiple docs in single pass.

### 4. Multimodal (Qwen3-VL)

Qwen3-VL-Plus highlights:
- OCR for scanned documents
- Layout understanding (tables, forms)
- Image + text reasoning
- Visual agent capabilities (GUI interaction)
- Diagram understanding
- Stamp + signature detection

**GovFlow use:** DocAnalyzer agent for scanned Vietnamese administrative documents.

### 5. Multilingual (119 languages)

Qwen3 trained on 119 languages including strong Vietnamese support.

**Benchmarks:** competitive with GPT-4 on Vietnamese benchmarks.

**GovFlow use:** all agents operate in Vietnamese for Vietnamese legal documents + user interactions.

### 6. Reasoning + Chain of Thought

Qwen3 supports:
- System 1 (fast) / System 2 (slow) modes
- Chain-of-thought reasoning
- Tool-augmented reasoning loop
- ReAct pattern

**GovFlow use:** Compliance agent reasons step-by-step about law applicability; LegalLookup traverses graph iteratively.

### 7. Structured output

Qwen3 supports:
- JSON mode (strict JSON output)
- Grammar-constrained generation (via tool calling)
- Function call schemas

**GovFlow use:** Drafter agent outputs strict JSON matching NĐ 30/2020 template structure.

## Benchmarks (as of 2026)

On standard benchmarks (MMLU, HumanEval, etc.), Qwen3-Max is competitive with:
- GPT-4 (OpenAI)
- Claude 3.5 Sonnet (Anthropic)
- Gemini 1.5 Pro (Google)
- DeepSeek-V2

On Vietnamese-specific benchmarks, Qwen3 typically outperforms US-based models due to language coverage.

## Strengths for GovFlow's use case

1. **Vietnamese fluency** — critical for user-facing content
2. **Long context** — handles full legal documents
3. **Multimodal** — OCR Vietnamese scanned docs
4. **Tool use** — orchestrate multi-agent workflows
5. **Open-weight** — deployable on-prem for data residency
6. **Alibaba Cloud integration** — Model Studio + Hologres AI Functions
7. **Reasonable pricing** — cheaper than GPT-4 by 30-50%

## Known limitations

### Gremlin generation
- Less training data on Gremlin compared to Cypher
- **Mitigation:** Gremlin Template Library + SDK Guard validation

### Tool use with many tools
- Can get confused with >30 tools in context
- **Mitigation:** per-agent scoped tool lists (only relevant tools per agent)

### Strict JSON adherence
- Occasionally adds extra text around JSON
- **Mitigation:** parse with error recovery, retry with strict prompt

### Hallucination on Vietnamese legal terms
- Sometimes invents citations if not grounded
- **Mitigation:** GraphRAG grounding via KG traversal (retrieval-first, generate-second)

## How GovFlow maximizes Qwen3

### 8 distinct roles (pitch-ready)

1. **Qwen3-Max as Graph Orchestrator (MCP)** — show agent mastery
2. **Qwen3-Max Planner DAG** — show reasoning
3. **Qwen3-Max + GraphRAG legal** — show hybrid RAG
4. **Qwen3-VL multimodal OCR** — show multimodal
5. **Qwen3-Max compliance reasoning** — show domain expertise
6. **Qwen3-Max classifier grounded** — show structured output
7. **Qwen3-Max summarizer (role-aware)** — show audience adaptation
8. **Qwen3-Max Drafter with guardrail** — show controlled generation

### Plus Hologres AI Functions (inline LLM in SQL) = 9th role for wow factor.

## Migration path: Model Studio → On-prem

For customer needing strict data residency:

```python
# Code stays the same
client = OpenAI(
    api_key='your-key',
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"  # hosted
)

# Just switch URL for on-prem
client = OpenAI(
    api_key='local-secret',
    base_url="http://on-prem-qwen:8000/v1"  # self-hosted via vLLM
)
```

### Hardware for on-prem Qwen3-32B
- Minimum: 1x NVIDIA A100 80GB
- Recommended: 2x A100 80GB (tensor parallel)
- Optimal: 4x H100 (for scale)

### Inference framework
- **vLLM** (recommended) — fast, production-ready
- **TGI (Text Generation Inference)** — Hugging Face alternative
- **DeepSpeed-FastGen** — alternative
- **Alibaba PAI-EAS** — managed on-prem option

## Prompt engineering tips for Qwen3

### System prompt
- Write in Vietnamese for Vietnamese tasks (cultural context)
- Be specific about role + constraints
- Reference authoritative sources (luật, nghị định)

### Few-shot examples
- Always provide 2-5 examples for tasks like classification
- Examples should cover edge cases
- Stored in Gremlin Template Library or prompt templates

### Structured output
- Use JSON mode when possible
- Provide schema in prompt
- Retry with clearer prompt if parsing fails

### Tool descriptions
- Write clear, specific descriptions
- Include parameter types + examples
- Reference when to use vs not use

### Temperature
- Compliance + legal tasks: 0.1 (deterministic)
- Summarization + drafting: 0.3 (slight creativity)
- Never > 0.5 for gov use case

## Monitoring Qwen3 in production

Metrics to track:
- Latency p50/p95/p99 per agent
- Token usage per case
- Error rate (JSON parse fail, API timeout)
- Tool call success rate
- Hallucination indicators (cite errors, fact errors)

## Cost optimization

1. **Prompt caching** — Qwen3 supports it, 40% savings on repeated prompts
2. **Smaller models for simple tasks** — Classifier uses Qwen3-Turbo instead of Max (10x cheaper)
3. **Batch processing** — off-peak batch for non-urgent tasks
4. **Response caching** — cache results for repeated case patterns

## Further reading

- **Qwen3 GitHub:** https://github.com/QwenLM/Qwen3
- **Qwen3-VL GitHub:** https://github.com/QwenLM/Qwen3-VL
- **Qwen Hugging Face:** https://huggingface.co/Qwen
- **Qwen blog:** https://qwenlm.github.io/blog/
- **Qwen research:** https://qwen.ai/research
- **Model Studio docs:** https://www.alibabacloud.com/help/en/model-studio/qwen-api-reference/

## When to use which model in GovFlow

| Task | Model | Reason |
|---|---|---|
| Heavy reasoning | Qwen3-Max | Flagship capability |
| Multimodal (OCR) | Qwen3-VL-Plus | Visual understanding |
| Simple classification | Qwen3-Turbo | Cost optimization |
| Embeddings | Qwen3-Embedding v3 | Specialized |
| On-prem production | Qwen3-32B | Open weight, deployable |
