# GraphRAG References — Papers + blogs

## Core research backing for GovFlow

### 1. AGENTiGraph — arxiv 2508.02999 (2025)

**Title:** "AGENTiGraph: A Multi-Agent Knowledge Graph Framework for Interactive, Domain-Specific LLM Chatbots"

**Key findings:**
- 7-agent architecture for knowledge graph interaction:
  1. User Intent Agent
  2. Key Concept Extraction Agent
  3. Task Planning Agent
  4. Knowledge Graph Interaction Agent
  5. Reasoning Agent
  6. Response Generation Agent
  7. Update Agent
- **95.12% accuracy** vs **83.34% zero-shot GPT-4o** on knowledge-intensive tasks
- Uses Neo4j via Bolt protocol
- Multi-step reasoning with graph traversal

**Why it matters for GovFlow:**
- Proves multi-agent + KG >> single LLM call for complex domains
- Provides reference architecture we extend (10 agents instead of 7, with permission layer)
- Research backing for Qwen3 agent patterns

**URL:** https://arxiv.org/html/2508.02999v1

**GovFlow adaptations:**
- Expanded to 10 agents with domain-specific roles for TTHC công
- Added 3-tier permission engine (not in AGENTiGraph)
- Dual graph design (static KG + dynamic Context Graph)
- Production deployment on Alibaba Cloud GDB

### 2. Neo4j "Agentic GraphRAG for Commercial Contracts" (2025)

**Key concepts:**
- Legal contracts have cross-references + version history
- Vector RAG alone insufficient for legal reasoning
- GraphRAG approach: structure contracts as graph + use LangGraph agents
- Users can query specific contract terms with full traceability

**Why it matters for GovFlow:**
- Vietnamese law has same structure (cross-references, amendments)
- LegalLookup agent uses same pattern for Luật/NĐ/Thông tư
- Proves legal domain specifically benefits from GraphRAG

**URL:** https://towardsdatascience.com/agentic-graphrag-for-commercial-contracts/

**GovFlow adaptations:**
- Target Vietnamese law corpus instead of commercial contracts
- Alibaba Cloud GDB instead of Neo4j
- Gremlin instead of Cypher
- Additional ABAC-on-graph layer for gov security

### 3. Microsoft GraphRAG (2024)

**Key concepts:**
- Build knowledge graph from text corpus
- Use graph structure for better RAG
- Community detection + summary at multiple levels
- Vector embeddings + graph hybrid retrieval

**Why it matters for GovFlow:**
- Microsoft-proven pattern at scale
- Blueprint for hybrid vector + graph retrieval
- Shows production viability

**URL:** https://github.com/microsoft/graphrag

**GovFlow differences:**
- Focused on Vietnamese legal domain vs general text
- Multi-agent orchestration (GovFlow) vs single retrieval pipeline (GraphRAG)
- Permission enforcement (GovFlow) vs open access (GraphRAG)

### 4. Hyperight (2026) — "GraphRAG + MCP as new standard for agentic data architecture"

**Key claims:**
- GraphRAG is becoming 2026 standard
- MCP (Model Context Protocol) for tool exposure
- Beyond vector stores — structured knowledge needed
- Semantic Kill-Switch for data residency compliance

**Why it matters:**
- Validates GovFlow's 2026 positioning
- Mentions data residency (matches VN requirement)
- Establishes MCP as serious standard

**URL:** https://hyperight.com/agentic-data-architecture-graphrag-mcp-2026/

### 5. RAG in 2025 / 2026 — State of the art

Multiple sources confirm:
- Naive vector RAG insufficient for complex domains
- GraphRAG + Agentic = evolving standard
- Multi-step reasoning + tool use > single-shot
- Knowledge graph as "structured memory" for LLMs

**Key quote (from Squirro, 2026 state of RAG):**
> "Autonomous agents plan multiple retrieval steps, choose tools, reflect on intermediate answers, and adapt strategies for complex tasks, e.g., compliance checks across many systems."

## ABAC-on-Graph research

### Graph-Based ABAC Policy Enforcement (arxiv 2405.20762, 2024)

**Key findings:**
- Graph databases are ideal substrate for ABAC policy
- Policy evaluation = graph traversal (fast)
- Property-level security enabled by graph model
- Compared to traditional RBAC/ACL — more flexible + auditable

**Why it matters:**
- Foundation for GovFlow's 3-tier permission engine
- Justifies "policy as graph" pattern

**URL:** https://arxiv.org/pdf/2405.20762

### AWS Neptune blog — "Graph-powered authorization" (2024)

**Key findings:**
- Graph databases excel for relationship-based access control
- Can model user/resource/policy relationships as graph
- Query-based access check

**Why it matters:**
- Production validation of graph ABAC pattern
- Alibaba Cloud GDB (similar to Neptune) can do the same

**URL:** https://aws.amazon.com/blogs/database/graph-powered-authorization-relationship-based-access-control-for-access-management/

### Neo4j Graph Database Security (commercial)

**Key features:**
- Fine-grained access control (FGAC)
- Per-label and per-relationship privilege
- Property-level security
- Attribute-based filters

**Why it matters:**
- Pattern for what Alibaba Cloud GDB should offer
- Reference implementation

**URL:** https://neo4j.com/product/neo4j-graph-database/security/

## MCP research

### Anthropic MCP specification

**Why it matters:**
- Standard for LLM tool exposure
- Adopted by Qwen3 (Alibaba Cloud)
- Interoperable across LLM vendors

**Features:**
- Tools (function calling)
- Resources (read-only data access)
- Prompts (pre-built templates)
- Sampling (for client-side LLM calls)

**GovFlow usage:**
- Expose graph tools (query_template, query_ad_hoc, etc.) via MCP
- Expose case resource for agent access
- Permission layer wraps MCP tools

## Legal AI research

### Legal Contract QA with LangGraph (Neo4j, 2025)

Demonstrates agentic workflow on legal graph can:
- Answer specific questions about clauses
- Traverse cross-references
- Provide traceable citations
- Outperform pure vector RAG

Applied to commercial contracts, same pattern works for Vietnamese law.

### Faithfulness in Agentic RAG for e-Governance (MDPI, 2025)

Evaluates Agentic RAG systems specifically for e-governance applications. Key insights:
- Hallucination risk higher in legal/regulatory domain
- Citation grounding essential
- LLM-as-judge frameworks to measure faithfulness

**Why it matters:**
- Validates our focus on citations + traceability
- Provides evaluation framework we can adopt

**URL:** https://www.mdpi.com/2504-2289/9/12/309

## Qwen3 research

### Qwen3 release paper (2025)

- Trained on 36 trillion tokens in 119 languages
- Dense models 0.6B to 32B
- Sparse models 30B/235B (MoE)
- Function calling + MCP support
- Apache 2.0 license for open-weight variants

### Qwen3-VL Technical Report (arxiv 2511.21631)

- Flagship multimodal model from Alibaba
- Strong at: document understanding, GUI interaction, visual coding
- 256K context length, expandable to 1M
- Top global performance on benchmarks

**GovFlow use:**
- DocAnalyzer agent
- OCR + layout + stamp detection

## Additional references

### CISA AI Use Cases (2024)
Federal (US) AI usage examples — some transferable patterns for gov AI.

### Vietnamese CCHC report
Annual public administration reform reports confirm painpoints.

### PCI (Provincial Competitiveness Index)
Vietnamese business sentiment — TTHC consistently top-3 pain point.

## Research gaps GovFlow fills

Despite the research above, no one has published:

1. **Graph-native agentic platform for Vietnamese public services** (GovFlow is first)
2. **3-tier permission engine for multi-agent systems** (novel combination)
3. **Agentic GraphRAG applied to Vietnamese legal corpus** (novel application)
4. **Full Alibaba Cloud stack for gov AI** (blueprint)

This creates opportunity for:
- Whitepaper publication
- Conference presentation (Alibaba Cloud Day, Vietnam Gov Tech Summit)
- Academic paper (arxiv)
- Blog post series

Post-hackathon, publish findings to establish thought leadership.

## Reading order (if team wants to dive deep)

For team members who want to understand the research backing:

1. **Start here:** Hyperight 2026 article (short, opinion piece)
2. **Core paper:** AGENTiGraph arxiv (30 min read)
3. **Practical application:** Neo4j Agentic GraphRAG blog (15 min)
4. **Security angle:** arxiv 2405.20762 Graph ABAC (45 min)
5. **Evaluation framework:** MDPI Agentic RAG faithfulness paper (30 min)

Total: ~2.5 hours reading for strong research grounding.

## Citation format for pitch

When referring to research in pitch:
> "AGENTiGraph paper from August 2025, published on arxiv, showed multi-agent knowledge graph architecture achieves 95% accuracy versus 83% for zero-shot GPT-4o on knowledge tasks. GovFlow adapts this pattern for Vietnamese public services with additional permission engine."

Short, specific, credible.
