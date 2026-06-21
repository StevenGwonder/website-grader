# ADR 004: AI as an Interpretation Layer

* **Status:** Accepted
* **Date:** 2026-06-21
* **Author:** Antigravity (Ponytail Coder)

## Context
Relying entirely on deterministic regular expressions or CSS selectors results in rigid checks that fail on complex content analysis (e.g., evaluating true brand consistency, intent classification, or conversion readiness). 
Conversely, passing raw page HTML to large language models (LLMs) to perform audits is expensive, slow, prone to hallucinations (e.g., inventing fake phone numbers or addresses), and leads to non-deterministic, untraceable results.

## Decision
We will establish a strict **governance boundary** for AI integration:
1. **Deterministic Core:** All diagnostic checks (Layer 2) remain fully deterministic. No AI is used to decide if a structured header or tag passes or fails.
2. **AI Interpretation:** AI is used strictly as an *interpretation and synthesis* layer (Layer 4) on top of collected deterministic evidence.
3. **Synthesis & Guidance:** The LLM will parse the structured list of failures/evidence to write custom fix instructions, summarize results, and generate exact, safe code templates (precluding placeholder coordinates or phone numbers).
4. **Token Control:** Enforce strict token limits (maximum input/output limits) and leverage structured outputs (Pydantic schema validation) to control API cost margins and ensure reliability.

## Consequences
* **Positive:** Bulletproof repeatability. Checks will not pass/fail randomly based on LLM temperature or prompts.
* **Positive:** Low and predictable token cost. We only feed synthesized data, not megabytes of raw HTML.
* **Negative:** Content nuances that cannot be evaluated deterministically will be classified as unverified rather than audited.
