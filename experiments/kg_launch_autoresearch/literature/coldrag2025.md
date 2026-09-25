# ColdRAG (2025 preprint)

URL: https://arxiv.org/html/2505.20773

ColdRAG uses an LLM to generate item profiles and a dynamic KG, then performs LLM-scored multi-hop candidate retrieval. Its Amazon protocol applies core filtering, designates the least frequent 10 percent of items as cold, and samples 500 test sequences. This is relevant to dynamic KG construction but not a strict zero-interaction launch protocol. Repeated LLM edge scoring is also a latency target for a lightweight patch.

