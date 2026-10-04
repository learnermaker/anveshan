# Model Gateway Conventions

**Status:** DECIDED implementation convention
**Purpose:** Keep Gemini/provider behavior replaceable, auditable, and replayable.

## Boundary

Track code should call a bounded model gateway/adapter:

    track logic → model gateway → provider adapter

The gateway returns an intermediate provider-neutral result and must not write directly to the eight common contracts.
Required path: model response → provider DTO → normalization → common contract → deterministic validation.

## Required run metadata

Every model-backed operation must be attributable to provider/model, model configuration, prompt ID/version, input artifact/fixture ID, runtime class, run ID, and expected behavior/evaluation reference.

## Model responsibilities

Model output may interpret multimodal evidence, locate relevant evidence, propose candidate structured content, identify deviations, and draft teaching/feedback language.
Model output may not authoritatively decide provenance, consent, observed-vs-inferred state, rubric definition, rubric weights, pass semantics, deterministic score arithmetic, transmission gain, or expert approval.

## Failure behavior

Provider failures, timeouts, malformed responses, and unsupported output must be explicit failures. Do not fabricate a fallback claim merely to complete a schema.

## Replay

Live model calls are additive. Deterministic replay must use recorded/model-free fixtures and stable expected results.
When model behavior changes materially, update prompt/model metadata and evaluation fixtures rather than silently accepting drift.

## UI boundary

Raw model JSON must never be sent directly to the UI as authoritative product data. UI-facing data is derived from validated common contracts.