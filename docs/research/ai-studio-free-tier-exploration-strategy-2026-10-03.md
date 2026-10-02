# Exploration Protocol and AI Studio Free-Tier Strategy — 2026-10-03

## 1. Principle

During exploration and prototype development, prefer Google AI Studio / Gemini Developer API free-tier capabilities wherever technically adequate.

Paid usage should be treated as an exception for:

- a capability unavailable on the free tier;
- a final reliability test;
- a final production-like load test;
- a clearly identified demo requirement that cannot be reproduced within free limits.

Do not design the product around paid-only capabilities until the thesis has survived exploration.

This is not merely a cost policy. It is a discovery constraint: if a concept requires large paid inference volume just to prove its core value, it may be poorly scoped for a three-person hackathon team.

## 2. Current Google facts

Google states that new Gemini API accounts begin on the Free Tier and that eligible models are available up to their free-tier rate limits.

Google measures Gemini API limits primarily through requests per minute (RPM), input tokens per minute (TPM), and requests per day (RPD). Limits are per project rather than per API key, and preview/experimental models generally have more restricted limits.

Google AI Studio also currently provides a Google Cloud Starter Tier for eligible accounts, allowing up to two full-stack application deployments without setting up a Google Cloud project or billing account. Each deployment creates a Cloud Run service; Starter Tier has a two-service limit and a single Cloud Run region.

Important data-policy distinction: Google states that on the Free Tier, content may be used to improve Google products. Paid services have different data-use terms. Do not put sensitive/private real-world data into the Free Tier unless the team has verified that the intended data use is acceptable.

## 3. Development architecture principle

Separate the product from model-specific execution.

Use a thin internal Model Gateway:

    application
        |
        v
    Model Gateway
        |
        +-- free Gemini model
        +-- free/preview specialized model
        +-- optional paid model
        +-- deterministic/mock evaluator
        |
        v
    normalized result

The application should not call a particular model directly throughout the codebase.

The gateway should record:

- model;
- request type;
- input modality;
- estimated token/input size;
- output size;
- latency;
- success/failure;
- rate-limit event;
- evaluation case;
- whether the call is deterministic, cached, recorded, or live.

## 4. Free-tier-first test strategy

### Tier 0 — Deterministic local tests

No model call.

Use:

- fixtures;
- saved model outputs;
- synthetic media;
- mocked retrieval;
- mocked evaluation;
- schema validation;
- unit tests;
- replay tests.

Goal: test application logic without consuming quota.

### Tier 1 — Small Gemini calls

Use free-tier models for:

- prompt development;
- schema design;
- extraction experiments;
- classification;
- simple reasoning;
- UI iteration;
- error handling.

Use short contexts and constrained outputs.

### Tier 2 — Multimodal spot tests

Use a small number of carefully selected videos/images/audio examples.

Do not repeatedly submit the same large media during development.

Cache:

- transcripts;
- extracted frames;
- model responses;
- embeddings;
- intermediate structured representations.

### Tier 3 — Specialized preview models

Test Gemini Robotics ER 2 only when the research question specifically requires embodied/spatial/temporal reasoning.

Because it is a preview model and has more restrictive limits, use it for targeted experiments rather than as the default model for every request.

### Tier 4 — Paid validation

Only after the thesis and architecture have survived free-tier testing.

Use paid capacity for:

- high-volume benchmark runs;
- final reliability tests;
- larger media processing;
- production-like concurrency;
- final demo rehearsal if required.

## 5. Quota-aware experimentation

Every experiment must have an explicit budget.

Example:

    Experiment: temporal skill evaluation
    Cases: 20
    Model calls/case: 2
    Maximum calls: 40
    Media variants: 2
    Fallback: replay recorded outputs

Do not run open-ended exploratory loops against the API.

For every experiment, record:

- hypothesis;
- cases;
- maximum calls;
- expected output;
- acceptance criterion;
- actual usage;
- failures;
- conclusion.

## 6. Build a replayable evaluation harness early

The most important engineering investment before UI polish is a replayable evaluation harness.

    golden case
       |
       v
    normalized input
       |
       v
    model gateway
       |
       +---- live call
       |
       +---- recorded response
       |
       v
    evaluator
       |
       v
    metrics

A developer should be able to run the full application against recorded model responses without making a single API request.

This gives us:

- reproducible demos;
- offline development;
- regression testing;
- quota preservation;
- model comparison;
- fast iteration.

## 7. Treat media as expensive

For video/audio experiments:

1. record once;
2. preserve the raw source;
3. create short benchmark clips;
4. derive transcripts once;
5. derive selected frames once;
6. store structured observations;
7. replay intermediate results locally;
8. call the model only when changing the hypothesis.

Do not repeatedly upload a 10-minute video simply to adjust a UI label.

## 8. Model routing strategy

Use the cheapest adequate model for each job.

Example:

    UI classification
        -> small/fast model

    transcript cleanup
        -> fast model or deterministic logic

    structured extraction
        -> fast multimodal model

    difficult reasoning
        -> stronger model only for selected cases

    embodied/spatial reasoning
        -> Robotics ER only when required

    evaluation benchmark
        -> selected model + human reference

The system must never use a frontier model simply because it is available.

## 9. Cache at semantic boundaries

Cache outputs at these boundaries:

- transcription;
- source segmentation;
- frame selection;
- object/scene observations;
- extracted claims;
- evidence links;
- embeddings;
- retrieval results;
- generated teaching plan;
- learner evaluation;
- final feedback.

A change to the UI should not trigger a new multimodal inference call.

A change to the retrieval prompt should not require retranscribing the media.

A change to feedback wording should not require re-running skill detection.

## 10. Exploration model matrix

For every candidate product thesis, run a minimal feasibility experiment before building infrastructure.

Columns:

- thesis;
- core capability;
- minimum model call;
- input modality;
- candidate free-tier model;
- specialized preview model required?;
- paid model required?;
- expected calls;
- media size;
- measurable output;
- failure mode;
- fallback;
- conclusion.

This prevents the team from discovering halfway through implementation that the core idea depends on an unavailable or expensive capability.

## 11. Google AI Studio as the laboratory

Use AI Studio as the fastest experimental surface for:

- prompt prototyping;
- model comparison;
- multimodal experiments;
- structured outputs;
- quick demos;
- Build mode prototypes where appropriate.

Then move stable logic into the repository.

AI Studio should be the **laboratory**, not the source of truth for the product.

The repository remains the source of truth for:

- prompts;
- schemas;
- evaluation cases;
- model configuration;
- recorded outputs;
- benchmark results;
- architecture;
- documentation.

## 12. Cloud deployment strategy

Use Cloud Run for the deployable prototype where appropriate.

Keep the architecture small:

- one frontend/service;
- one backend/API;
- one object-storage boundary;
- one database/vector/index layer only if necessary;
- model gateway.

Avoid premature microservices.

If the AI Studio Starter Tier is available to the account, it may be useful for early public deployment. Google currently states that eligible accounts can publish up to two full-stack applications through the Starter Tier.

For the competition deployment, verify the official submission requirements and use the required Google Cloud deployment path.

## 13. Data policy for experiments

Because Free Tier data may be used to improve Google products, default exploration data should be:

- synthetic;
- public-domain;
- explicitly permitted;
- team-created;
- non-sensitive.

If we record a real expert, verify the data-use implications before sending identifiable recordings through a Free Tier project.

Do not assume that "public on YouTube" means "safe to upload into any processing pipeline."

## 14. Demo strategy

The final demo should use a stable, prevalidated path.

Preferred:

    live UI
       +
    preprocessed source
       +
    deterministic fixture
       +
    limited live Gemini calls
       +
    recorded fallback

A demo should never depend on making 20 unpredictable API calls in sequence.

The audience should see genuine AI inference, but the team should control unnecessary quota consumption and failure points.

## 15. Cost-risk rule

For every candidate architecture ask:

> What percentage of the core demo requires paid inference?

If the answer is close to 100%, investigate whether the concept can be narrowed.

If the core proof works with:

- free Gemini calls;
- cached intermediate artifacts;
- deterministic evaluation;
- limited specialized-model calls;

that is a much healthier hackathon architecture.

## 16. Current preferred experimentation order

1. Local deterministic prototype.
2. AI Studio prompt experiments.
3. Small free-tier API tests.
4. Multimodal spot tests.
5. Specialized Robotics/world-model experiments.
6. Golden evaluation set.
7. Full application integration.
8. Public Cloud Run prototype.
9. Paid load/reliability test only if necessary.
10. Final demo rehearsal.

## 17. Important caveat

Free-tier limits are not a fixed entitlement to a particular number of calls. Google states that limits vary by model and project and that actual capacity can vary. Always inspect the active limits in AI Studio before a large experiment.

Preview models are particularly unsuitable for assuming a generous stable quota.

## 18. Strategic implication

The free-tier-first constraint should influence product selection.

Prefer ideas where:

- one or a few multimodal calls produce a meaningful insight;
- intermediate representations can be cached;
- deterministic logic can handle orchestration;
- evaluation can run offline;
- the demo does not require high-volume generation;
- specialized models are used selectively.

Avoid ideas whose value proposition depends on:

- continuous expensive video inference;
- high-frequency live multimodal calls;
- massive corpus processing;
- large-scale synthetic simulation;
- repeated frontier-model inference.

The goal is not to build the cheapest product.

The goal is to discover and prove the strongest product **without wasting scarce inference capacity on engineering that does not increase evidence of value**.

## 19. Decision rule

For each shortlisted thesis, require:

> Core value demonstrable on free-tier or locally replayed inference: YES/NO

> Specialized preview dependency: LOW/MEDIUM/HIGH

> Paid dependency: LOW/MEDIUM/HIGH

> Offline/replay fallback: YES/NO

> Final demo quota risk: LOW/MEDIUM/HIGH

Any candidate with HIGH paid dependency and HIGH demo quota risk requires an unusually strong reason to survive.

## Sources

- Google Gemini API Billing: https://ai.google.dev/gemini-api/docs/billing
- Google Gemini API Pricing: https://ai.google.dev/gemini-api/docs/pricing
- Google Gemini API Rate Limits: https://ai.google.dev/gemini-api/docs/rate-limits
- Google AI Studio deployment: https://ai.google.dev/gemini-api/docs/aistudio-deploying
- Gemini Robotics ER: https://ai.google.dev/gemini-api/docs/robotics-overview
- Google AI Studio / Google Cloud Starter Tier documentation: https://ai.google.dev/gemini-api/docs/aistudio-deploying
