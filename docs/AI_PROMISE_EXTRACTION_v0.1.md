# Iteration 004 — source-linked promise proposals (synthetic only)

## Separation of responsibilities

1. **Source event**: an immutable `manager_message` previously imported from the **synthetic** source. User cannot send arbitrary raw message text to this endpoint.
2. **Candidate generator**: `SP_AI_PROVIDER=rules` (default, **NOT AI**), `SP_AI_PROVIDER=openai` (optional real external LLM integration, **not invoked in CI**), or `off`.
3. **Independent validation**: the candidate must quote an *exact substring* of that immutable event; promise to **send a quote today by an explicit HH:MM**; due date equals the date of the message in `Europe/Moscow`; HH:MM matches the literal source quote; is timezone-aware, after the source message, and has no seconds. Wrong day, time, actor, span or malformed text => **ABSTAIN**. Only healthy, watermarked sources qualify.
4. **Human approval**: `POST /api/v1/ai/proposals` is **read only**. The supervisor checks and manually approves the source event and deadline through existing `POST /api/v1/commitments`. Only after this are normal deterministic rules allowed to evaluate coverage and later candidate overdue; the manager is **never accused by a model suggestion**.
5. **Audit**: existing `HUMAN_APPROVED` audit event records approval. No raw LLM output or unchecked suggestion enters a commitment.

## API

Authenticated **supervisor only**:

```bash
curl -fsS -X POST http://127.0.0.1:18080/api/v1/ai/proposals \
  -H 'Authorization: Bearer dev-only-supervisor-token' \
  -H 'Content-Type: application/json' \
  -d '{"source_id":"demo-instagram","conversation_id":"demo-lead-001"}'
```

Response fields:
- `provider`: `RULE_BASELINE_NOT_AI` / `OPENAI` / `OFF`
- `proposals[]`: source, conversation, event ID, actor, *verbatim* evidence quote, explicit timestamp and `PROPOSED_NOT_APPROVED`
- `abstentions[]`: bounded reason code (`NO_VERIFIABLE_EXPLICIT_PROMISE`, `INSUFFICIENT_SOURCE_COVERAGE`, `PROVIDER_ERROR`, etc.)
- `review_required=true`, `data_mode=SYNTHETIC_ONLY`
- `confidence=null`, `financial_impact=null`, no model scoring.

The dashboard presents the quote and deadline next to a button requiring separate explicit confirmation. A preexisting manually approved promise returns `created=false` (idempotent).

## Optional real model adapter (disabled in normal operation)

The code contains `app/ai_extract.py::_openai_candidate`. It uses the OpenAI **Responses API** with **structured JSON Schema** output (`text.format`, strict), `store=false`, a short 12s timeout, and server-side request validation. References:
- [OpenAI Responses API reference](https://platform.openai.com/docs/api-reference/responses/create)
- [Structured Outputs guide](https://platform.openai.com/docs/guides/structured-outputs)

The provider is only selected if **all** of these are configured on the **backend process**: `SP_AI_PROVIDER=openai`, `SP_AI_MODEL` (an available API model supporting JSON Schema), and `OPENAI_API_KEY`. Credentials must not enter source control, browser, screenshots, CI job logs, or chats. The shipped Docker Compose does **not** forward these values by default, to avoid accidentally sending even synthetic event text to a third party. If absent, the model path abstains. Never enable external processing on actual customer data without explicit consent, appropriate legal agreements and privacy review.

**Current evidence:** CI tests the rules baseline and *mocked* LLM results only; there is no live provider evaluation, no measured model precision, and no buyer pilot. The existence of an adapter must **not** be described as validated real-model behavior.

## Known boundaries

- Only explicit Russian promises to **send a quote today by HH:MM in Moscow local time** are accepted. Tomorrow, named days, unstated timezones, ambiguous deadlines, uncertain verbs, and other commitments intentionally abstain.
- No customer message classification, coaching, actual AI-generated financial loss, sentiment score, managerial ranking or automatic HR action.
- A correct-looking provider-generated quote is not trusted unless it passes the independent validator.
- Realtime privacy controls, provider rate limiting, live integration permission and stronger tenant auth are not implemented. `SP_MODE` is synthetic only.

## Evaluation

`fixtures/ai_eval.json` contains **13 synthetic examples**, four positives and nine negatives. `tests/test_ai_eval.py` asserts deterministic baseline TP=4, FP=0, TN=9, FN=0. This is a **tiny controlled smoke suite, not representative model accuracy**.

Other tests cover model-output hallucinated quote, wrong date/time/timezone, past deadlines, negation, permission denied, source-health missing, no auto-created commitment, and mock provider failures. Add **live held-out consented, labeled dialogs and an explicit quality gate** before claiming model usefulness or exposing third-party LLM calls.
