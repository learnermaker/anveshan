# User Journeys

## Journey 1 — Source Captures Knowledge

1. A source session begins.
2. Anveshan establishes context and source provenance.
3. The source may be an expert explanation/demonstration, a desired target state/image, a learner attempt, or a combination.
4. When applicable, the source can include tools, materials, environment, and exceptions.
5. Source media is preserved.
6. AI transcribes and analyzes.
7. Candidate knowledge is extracted.
8. Evidence links are attached.
9. Expert reviews.
10. Expert approves or corrects.
11. Knowledge becomes available according to permissions.

## Journey 2 — Learner Learns

1. Learner chooses a skill.
2. System checks prerequisites.
3. Learner receives a source-grounded experience appropriate to the source mode.
4. This may be a demonstration, target-conditioned workspace, or corrective explanation.
5. Learner can inspect evidence and ask questions.
6. Evidence-linked answers are shown.
7. System creates a bounded practice task.
8. Learner attempts the task.

## Journey 3 — Learner Is Evaluated

1. Learner submits video/audio/image/text evidence.
2. System identifies observable behavior.
3. System compares against reference demonstration or rubric.
4. System identifies differences.
5. System links feedback to evidence.
6. Uncertain judgments are marked uncertain.
7. Learner retries.
8. Improvement is measured.

## Journey 4 — Knowledge Evolves

1. Learner develops an adaptation.
2. Adaptation is documented.
3. Context is recorded.
4. Expert/community reviews where appropriate.
5. Adaptation becomes a variant/version.
6. New learners can learn the variant.
7. Lineage records the path.

## Journey 5 — Knowledge Scout

1. Scout analyzes the knowledge graph.
2. It identifies missing evidence or single-source areas.
3. It identifies possible knowledge holders.
4. It generates interview questions.
5. Expert is interviewed.
6. New evidence enters the graph.
7. Gap status changes.

## Journey 6 — Community Review

1. Community receives a review request.
2. Members inspect source and derived representation.
3. Community adds context.
4. Community approves, disputes, or restricts.
5. Access policy is updated.
6. Lineage records the governance event.


## Journey 7 — Creator Publishes a Skill (2026-10-07)

1. The creator uploads a demonstration (image, video or audio) and confirms they have the rights to it.
2. Anveshan shows what it measured and what the AI understood.
3. The creator checks and corrects the steps (edit or remove), then confirms "Looks right".
4. The creator practises it themselves (optional).
5. The creator publishes:
   - chooses credit (attribution name), a licence and the consent scope;
   - the skill goes to the steward's review queue.
6. The steward publishes it, or sends it back with a note.
7. Once published, anyone can practise it. The creator sees aggregate insights: where learners first go wrong, the hardest checks, and whether the feedback helped.
8. The creator improves the teaching (corrects or clarifies a step), which creates a new version.

## Journey 8 — Steward Curates the Library (2026-10-07)

1. The steward signs in with a steward access code (no accounts in the demo).
2. Overview:
   - what needs attention (submissions waiting, skills not yet checked, budget nearly used);
   - library size;
   - learner activity.
3. Review queue:
   - opens a skill with its source and the AI-extracted steps;
   - approves, corrects or removes steps;
   - publishes, sends back with a note, or rejects.
4. Library: unpublishes a skill that should not be public (moderation).
5. Consent and licences: checks credit, licence and consent per skill; exports the record.
6. Insights: sees which skills learners struggle with and where.
7. Usage: sees today's AI calls against the budget, storage, and blocked requests.
8. Durable decisions (e.g. an expert's review of a curated skill) are exported and committed. The demo server forgets runtime changes on restart, and the console says so.

## 2026-10-07 UX Rule — end-user-centric surfaces

- The learner surface contains no audit tooling: no claim identifiers, confidence numbers, approve/reject controls, run classes or lineage hashes.
- Trust reaches the learner through progressive disclosure:
  - a plain trust line;
  - "Show me in the source";
  - "Why this feedback?".
- Honesty labels stay visible in plain words.
- Review of the extracted representation belongs to the creator (for their own skill) and the steward (for the library).
- Each screen has one obvious primary action and a plain-language empty state.

## 2026-10-03 UX Rule

The learner journey must contain a visible baseline, a bounded task, criterion-level feedback and a retry. The expert journey must contain review of the extracted representation. These are not optional polish; they are the product proof.
