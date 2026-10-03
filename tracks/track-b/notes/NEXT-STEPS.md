# Track B — Next Steps

Start with the smallest deterministic replayable learner loop.

## First implementation issue

Define a domain-agnostic replay representation for:

`PracticeTask → baseline → attempt → evaluation → feedback → retry → measured change`

Do not select the final domain, skill, learner, or rubric here. M0 decides those inputs.

## After the first issue

Add model-assisted observation/comparison/feedback only where it provides measurable value and remains auditable.

Each AI change must carry:

- model/config;
- prompt version;
- rubric;
- fixture;
- evaluation result.

## Integration readiness

Track B is ready for integration when replay proves criterion-level evaluation, traceable feedback, retry handling, reproducible measurement, and transmission lineage for the selected bounded use case.
