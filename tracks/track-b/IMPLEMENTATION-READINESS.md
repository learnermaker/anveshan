# Track B — Implementation Readiness Checklist

Use this as the coding-agent gate. It complements SUCCESS-CRITERIA.md.

## Before implementation
- [ ] Read the common seam, validator, and frozen replay fixture.
- [ ] Confirm Track A can be represented by fixtures; do not wait for Track A code.
- [ ] Identify LearnerAttempt, Evaluation, Feedback, and TransmissionRecord as Track B outputs.
- [ ] Confirm the same learner/task/rubric frame is used for baseline and retry.
- [ ] Define observable criterion evidence and negative cases before live Gemini work.

## During implementation
- [ ] Keep evaluation criterion-first, not single-score-first.
- [ ] Preserve learner evidence and uncertainty.
- [ ] Keep rubric, score arithmetic, pass semantics, and gain deterministic.
- [ ] Keep Gemini behind a bounded evidence/interpretation adapter.
- [ ] Link feedback to evaluated criteria and evidence.
- [ ] Keep reusable code independent of domain, profession, tool, and modality.
- [ ] Keep UI projections downstream and replaceable.

## Integration gate
- [ ] Baseline is BASELINE/1; retry is RETRY/2+.
- [ ] Required criteria and score bounds validate.
- [ ] Feedback cannot target unevaluated criteria.
- [ ] Retry comparison uses the same rubric.
- [ ] Gain equals retry score minus baseline score and is independently reconstructable.
- [ ] Complete replay passes without live Gemini.
- [ ] Malformed/inconsistent bundles fail loudly.
- [ ] Track B does not import Track A implementation modules.

## Stop conditions
Stop if success requires changing a frozen contract, guessing unobservable learner behavior, coupling evaluation to the UI, choosing a domain merely because a model supports it, or adding generic LMS/analytics infrastructure.
