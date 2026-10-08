# K10: first-time-user and jury review of the whole app (observe only)

**What K10 is.** Before submission (2026-10-18), Kiro walks through the whole app the way a hackathon judge and a first-time user would: in a real browser through the Playwright MCP, on desktop and on phone, in every role. It records everything it sees in one structured report. **Kiro changes no product code in K10.** Claude Code reads the report, analyses it and writes the fixes (K11). The aim: after K11 the app is ready to submit. A first-time visitor understands it, can use it, and sees why it is new. Nothing looks like an afterthought or AI filler, and the core ideas show without being oversold.

**How it runs.** One Kiro session (the parent chat) launches one workflow: `.kiro/workflows/k10-review.workflow.yaml`. Only one Playwright browser exists, so the browser walks run **one after another** in one branch. A second branch runs the checks that need no browser **in parallel**. A jury step and a compile step finish.

```
setup ─┬─ browser branch: W1 → W2 → W3 → W4 → W5 → W6 → W7   (Playwright, sequential)
       └─ static branch:  S1 → S2 → S3                          (no browser)
     → jury → compile → REPORT.md
```

---

## 0. For Jim: how to start

1. Pull `main` in `C:\Users\JIMSEELAN\Desktop\Projects\hackathons\anveshan` and open **that folder** in Kiro.
2. Check that Workflows are on (Settings → Features → Workflows), the model is **Claude Sonnet 4.6**, and the **playwright** MCP server is enabled. It is enabled in `~/.kiro/settings/mcp.json`. If Kiro asks to install a browser, allow it.
3. Paste this into a **new** chat:

> Run the K10 review. Read `docs/kiro/specs/K10-REVIEW.md` sections 1–5 and `.kiro/steering/k9-run-rules.md` first. K10 overrides rules 2 and 3 there: you change no tracked file, and you write only under `.kiro/k10-run/`. Validate `.kiro/workflows/k10-review.workflow.yaml` with validate_workflow. If an agent name is unknown, swap it as in `K9-ORCHESTRATOR.md` §5.6 and validate again. Then launch the `k10-review` workflow with no inputs. Stay in this chat as the orchestrator. Every 20 minutes, and whenever a step reports, read `.kiro/k10-run/STATUS.md` and pass on any new `.kiro/k10-run/INBOX.md` entries. Answer step questions with the defaults in §9. Ask me only if a human is needed. If workflows are unavailable, run the steps yourself in the order in §10. Finish by telling me where `REPORT.md` is and how many observations of each severity it has.

4. Claude Code reads `.kiro/k10-run/` while the run is going. To steer it, append to `.kiro/k10-run/INBOX.md` (format in §5.3).

---

## 1. Read before acting (every step)

1. This file, at least §1–§5 plus your own section.
2. The product brief: `docs/kiro/specs/K9-00-PRODUCT-UX.md`, §2 (roles), §3 (UX principles) and §5 (copy dictionary). This is the yardstick for "is this screen right".
3. The positioning: `docs/product/novelty-boundary.md#skills-of-the-physical-world-positioning-decided-2026-10-07`. This is the yardstick for "does the innovation show".
4. The judging criteria: `docs/kiro/official-rules-2026-10-06.md` §"Judging Criteria".
   - Technical Merit & Gen AI: 40%.
   - Problem Alignment & Impact: 25%.
   - Innovation & Creativity: 25%.
   - UX & Solution Design: 10%.

Do **not** read the older specs (K1–K9 task specs), golden runs, `app/src/data/cases/registry.ts`, media or large JSON.

## 2. Rules for K10 (on top of `.kiro/steering/k9-run-rules.md` rules 1, 4, 5, 7, 8 and 9)

1. **Observe, don't fix.** Never edit, commit or push anything tracked in git, and never switch branches. If a fix is obvious, write it as a one-line `suggestion` in the observation. Claude Code decides.
2. **Write only under `ROOT\.kiro\k10-run\`.** This folder is gitignored. `ROOT` is `C:\Users\JIMSEELAN\Desktop\Projects\hackathons\anveshan`.
3. **Fresh eyes first.** At the start of each walk, write down what you expect and what you understood *before* reading code or docs about that screen. Judges see the screen, not the code. Read code only afterwards, to explain a bug you have already seen. Mark those notes `code-checked`.
4. **Quote, don't paraphrase.** Every copy observation quotes the exact visible text in double quotes.
5. **Evidence for everything.** Each observation has at least one of:
   - a screenshot file;
   - a console or network line;
   - a quoted text snippet with its URL.
6. **Live AI budget: at most 40 model calls in the whole run**, all through the local server's own key. In the app, these happen only when you upload in the composer or upload your own attempt.
   - Never type, paste or read any API key, and never open `.env`.
   - If the app asks for a Gemini key, do **not** enter one. Record what the screen says, choose the no-key path (cancel, or "use the demo"), and continue.
   - Log every call you trigger in `.kiro/k10-run/live-calls.md`: time, walk, action and outcome. The steward Usage tab shows the server's count; compare the two at the end of W5.
7. **Steward code** is the local test value `local-test-code`. It is set by `start-svc.ps1` (§3.2). It is only a local test value; never use it anywhere else.
8. **Uploads** come only from the repo files in §6.6. Never upload anything from outside the repo.
9. **Don't stop on failure.** If something is broken, record it, take a screenshot, and work around it (reload, go back, use the URL in §6.0). Then continue. A walk ends with "blocked at step N" only if nothing at all can continue.
10. **Token hygiene.**
    - Prefer `browser_snapshot` (accessibility tree) for reading text and finding elements.
    - Use `browser_take_screenshot` (an image you look at) when judging looks, layout, media or charts.
    - Save the full-page files for Claude Code with `browser_run_code` (§4.3).
    - Don't paste whole snapshots into your notes.

## 3. Setup (workflow step `setup`)

### 3.1 Run folder
Create these under `ROOT\.kiro\k10-run\`:
- `STATUS.md` (the board, §5.1);
- `INBOX.md` (with the header `# K10 inbox`);
- `live-calls.md`;
- folders `obs\`, `shots\`, `data\`, `logs\`.

### 3.2 Production-like server (what the jury will see on Cloud Run)
Run from `ROOT` in PowerShell, waiting for each command to finish:

```powershell
$py = "C:\Users\JIMSEELAN\Desktop\Projects\hackathons\anveshan\.venv\Scripts\python.exe"
& $py tools/fetch_media.py *> .kiro/k10-run/logs/fetch_media.log   # case media + browser-playable .mp4 copies of .ogv (first run ~4 min)
npm --prefix app run build *> .kiro/k10-run/logs/build.log          # app/dist, served by the service as on Cloud Run
```

Write `.kiro\k10-run\start-svc.ps1`:

```powershell
$env:ANVESHAN_MODE = "recorded"
$env:ANVESHAN_STEWARD_OPEN = "0"
$env:ANVESHAN_STEWARD_TOKEN = "local-test-code"
$env:ANVESHAN_DATA_DIR = "C:\Users\JIMSEELAN\Desktop\Projects\hackathons\anveshan\.kiro\k10-run\data"
$env:ANVESHAN_DAILY_CALL_BUDGET = "60"
Set-Location "C:\Users\JIMSEELAN\Desktop\Projects\hackathons\anveshan"
& "C:\Users\JIMSEELAN\Desktop\Projects\hackathons\anveshan\.venv\Scripts\python.exe" -m uvicorn anveshan_service.main:app --app-dir service --port 8080 *> .kiro\k10-run\logs\service.log
```

Start it in the background:

```powershell
Start-Process powershell -WindowStyle Hidden -ArgumentList '-ExecutionPolicy','Bypass','-File','.kiro\k10-run\start-svc.ps1'
```

Then:
- If port 8080 is already in use, stop that process first: `Get-NetTCPConnection -LocalPort 8080 | % { Stop-Process -Id $_.OwningProcess -Force }`.
- Wait until `curl.exe --ssl-no-revoke -s http://localhost:8080/api/health` returns JSON (up to 60 s).
- Check that `curl.exe -s -o NUL -w "%{http_code} %{content_type}" http://localhost:8080/api/media/origami-crane/src.origami-crane.demo.v1` prints `200 video/mp4`. If it doesn't, record observation `SETUP-1`.
- **The app is http://localhost:8080/** (the built app served by the service). Do not use the Vite dev server (5173).

### 3.3 Baseline numbers (record in `STATUS.md`)
- Build: success or failure, and the bundle size line from `build.log`.
- The health JSON (mode, model names; never keys).
- Commit: `git rev-parse --short HEAD`.

When setup is done, call `send_message` (success) with a one-line summary.

## 4. How to observe

### 4.1 Observation record
Each walk writes `.kiro\k10-run\obs\<WALK>.md`:
1. A short **narrative** (what you did, in order, at most 40 lines).
2. The **first-impression answers** (§4.4).
3. The **observations**, one block each, in exactly this shape. Claude Code parses it.

```markdown
### <WALK>-<nn> · <S0|S1|S2|S3> · <category>
- where: <URL incl. ?view=…&case=…> · <desktop|phone> · <role: learner|creator|steward|visitor>
- step: <what you were doing>
- saw: <what happened; quote exact text in "…">
- expected: <what a first-time user / judge would expect>
- why it matters: <one line: which judging criterion or which user it hurts>
- evidence: <shots\W1-03.png | console: "…" | network: GET /api/… 404>
- confidence: <high|medium|low>
- suggestion: <optional, one line; never code>
```

**Severity:**
- **S0 blocker**: a judge would stop, or would conclude the app is broken: a crash, a blank screen, media that won't play, a core flow that can't be finished, wrong results, a leaked secret.
- **S1 major**: hurts understanding, trust or the judging score: confusing flow, a hidden key innovation, AI filler copy, a misleading claim, a broken secondary flow, phone layout broken.
- **S2 minor**: noticeable roughness: inconsistent wording, a weak empty state, slow without feedback, alignment.
- **S3 polish**: nice to have.

**Category** (pick exactly one):
- `bug`: wrong behaviour or an error.
- `media`: an image, video or audio that won't load, play or seek.
- `flow`: order of steps, dead ends, no clear next step.
- `clarity`: a first-timer can't tell what this is or what to do.
- `copy`: wording, tone, jargon, typos, inconsistent terms.
- `fluff`: AI-agent filler, marketing adjectives, repeated explanations, sections that serve no user.
- `afterthought`: looks bolted on: placeholders, debug text, raw file names or IDs, mismatched styles, a stale "prototype" feel.
- `innovation-hidden`: a key idea (§4.5) is present but a first-timer would miss it.
- `innovation-overdone`: a key idea is over-explained, repeated or oversold ("nobody does this", superlatives).
- `honesty`: a missing, wrong or confusing honesty label; synthetic content presented as real; overclaiming.
- `a11y`: keyboard, focus, contrast, labels, text size, screen-reader names.
- `layout`: phone or desktop layout, overflow, horizontal scroll, overlap.
- `performance`: slow loads or waits; a missing progress message.
- `consistency`: the same thing named or styled differently in different places.
- `delight`: something that works especially well. Record these too, with severity S3, so we don't break them.

### 4.2 Viewports
- **desktop** is 1440×900.
- **phone** is 375×812. Use `browser_resize`, then reload.

At the start of each walk, open a **fresh context**: `browser_close`, then navigate. Every walk is a first visit. Clear storage with `browser_evaluate` running `localStorage.clear(); sessionStorage.clear()`, then reload.

### 4.3 Screenshots
- To judge a screen, use `browser_take_screenshot` and look at it.
- To keep a full-page file for Claude Code, run this with `browser_run_code`:

  ```js
  async (page) => { await page.screenshot({ path: 'C:/Users/JIMSEELAN/Desktop/Projects/hackathons/anveshan/.kiro/k10-run/shots/<WALK>-<nn>.png', fullPage: true }); }
  ```

- Save one file for **every screen you visit**, plus one for every S0/S1 observation.
- Name the files `<WALK>-<nn>-<short-name>.png` (example: `W2-04-crane-source-video.png`).

### 4.4 First-impression protocol (each walk, before you interact)
On the walk's first screen, before clicking anything, look at one screenshot and answer in `obs\<WALK>.md`:
1. **5-second test:** what is this product, in one sentence? Who is it for? What would you click first?
2. **What is new here, compared with YouTube, a chat tutor or an online course?** Answer only from what is on screen.
3. **Does anything look unfinished, generic or AI-written?** Quote it.

At the end of each walk, answer:
4. **Explain-back:** describe what the app did for you, in three sentences, as you would to a friend.
5. **Moments:** list where you were confused (the observation IDs) and where you were impressed.
6. **Would a judge keep going after 2 minutes?** Yes or no, and why.

### 4.5 Key ideas to look for (and judge: visible, understood, not overdone)
For each idea, every walk notes: where it shows (URL and element), how many clicks it takes to reach, whether a first-timer would notice it and understand it, and whether it is over-explained.

| # | Key idea | What "done well" looks like |
|---|---|---|
| K1 | The real thing in, the real thing checked: source and attempt are a photo, video or audio of physical work | the attempt screen asks for a capture of the real world ("film your hands"), not a text answer |
| K2 | The AI turns any demonstration into steps and checks (universal pipeline), and a person reviews them | the composer shows "what the AI understood" and lets the creator correct it |
| K3 | First divergence: where you first went off track | one clear moment, not a wall of scores |
| K4 | Feedback points back to the source moment (a frame, time or region) | a "show me in the source" link that jumps the video or highlights the region |
| K5 | The AI never sets the score; fixed rules do | stated once, briefly, where scores appear; checkable on the evidence page |
| K6 | Honest about what can't be sensed (pressure, touch) and about the source (synthetic, internet, not expert-checked) | labels visible but calm, in plain words |
| K7 | Retry and measured change (transmission gain) | results compare try 1 and try 2, check by check |
| K8 | Credit, consent and review: creator credit, steward review queue, licences | visible in the creator and steward flows; one credit line for learners |
| K9 | Uses Gemini meaningfully (multimodal perception and coaching wording) on Google Cloud | apparent to a judge without reading code; not buzzword-heavy |

### 4.6 Things to check on every screen (quick checklist, record only failures)
- **One** obvious primary button. A one-sentence purpose at the top.
- No raw IDs, file names (`.ogv`, `.json`), enums, hashes, `undefined`, `null`, `NaN`, `[object Object]`, `TODO`, "lorem", or "coming soon".
- No console errors or warnings. Use `browser_console_messages` after each screen and record new errors. Also no failed requests (`browser_network_requests`, any 4xx or 5xx).
- Images load. Videos play, seek and show a picture: check `videoWidth > 0` with `browser_evaluate`. Audio plays.
- At phone width there is no horizontal scroll: `document.documentElement.scrollWidth <= innerWidth`. Nothing overlaps or gets cut off.
- Text is at least 12 px. Focus is visible when you tab through.
- Loading states say what is happening. Waits over 3 s show progress. Record how long each AI wait took.
- Terms are consistent across screens (e.g. "skill" vs "case", "practise" vs "practice", "try" vs "attempt").
- Honesty labels match §3.5 of the product brief.

## 5. Status and inbox

### 5.1 `STATUS.md` (written by setup, each walk at its start and end, jury and compile)
```markdown
# K10 status
| Step | State | Started | Finished | S0 | S1 | S2 | S3 | Note |
|---|---|---|---|---|---|---|---|---|
| setup | DONE | 10:02 | 10:09 | | | | | build ok, media mp4 ok |
| W1 | IN_PROGRESS | 10:10 | | 1 | 3 | | | |
```
Use these states: `TODO`, `IN_PROGRESS`, `DONE`, `BLOCKED` (with a reason).

### 5.2 Live calls: `live-calls.md` (§2.6)

### 5.3 Inbox entries (appended by Claude Code or Jim)
```markdown
## IN-<n> · <ISO time> · to: <W1..W7 | S1..S3 | ALL> · from: Claude | Jim · type: INSTRUCTION | CHANGED-ON-MAIN | QUESTION-ANSWER
<text>
```
Each step reads the inbox at its start and after every 5 observations. Acknowledge each entry in your `obs` file ("Inbox: handled IN-n").

---

## 6. Browser walks (branch `browser`, sequential, Playwright MCP)

### 6.0 Useful URLs (for recovery only; walks should navigate by clicking, as a user would)
- `/?view=discovery`: the library (home).
- `/?view=source&case=kolam`, `…&case=origami-crane`, `…&case=tabla`: the Learn page of each skill.
- `?view=practice&case=…` and `?view=transmission&case=…`: Practise and Results.
- `?view=composer`: share a skill.
- `?view=mine`: My skills.
- `?view=steward`: the steward console.
- `?view=evidence`: "How we check".

### 6.1 W1: first-time learner on desktop, Kolam (the main demo path)
**Persona:** Priya, 34, likes crafts, has never heard of Anveshan; arrived from the hackathon gallery. Desktop.
1. Land on `/`. Do §4.4 Q1–Q3. Read the whole home page top to bottom and record anything confusing, repeated, filler or unexplained. Examples to check: the section about design archetypes, "You have N skills in My skills" on a first visit, duplicate skill cards, attribution text that shows a file name.
2. Click the main call to action. On the Learn page: is it clear what you are about to learn and where it came from? Open every "why", "show me" or "details" disclosure. Check that the source image loads and that the steps link to regions of the source (K4).
3. Start practising. Draw the kolam in the browser with `browser_run_code`, using mouse moves on the canvas. Make it **deliberately imperfect**: a rough circle or partial loop is enough. Submit. Record the time to the result.
4. On the feedback: is the first point where you went off track clear (K3)? Does it link to the source (K4)? Is the suggested exercise concrete? Is it clear the score comes from rules (K5), without overdoing it?
5. Retry. This time also try **"use a sample attempt"** if offered (good, then flawed), and note how samples are labelled. Finish the retry.
6. Results: is the change between try 1 and try 2 understandable (K7)? Is it saved as a record, and what does that mean to Priya? Find and open the link to "how we check" (the evidence page) from here, if there is one.
7. Use the browser **Back** button at each stage and **reload** on Results. Does the state survive or break?
8. Do the end-of-walk answers (§4.4 Q4–Q6).

### 6.2 W2: first-time learner on phone, paper crane (video)
**Persona:** Arjun, 21, a student on a phone with slow patience. 375×812.
1. Land on `/`, do Q1–Q3, and check the phone layout of the home page (no horizontal scroll; tap targets).
2. Open the paper crane skill. **The source video must show a picture and play.** Check `videoWidth > 0`, press play, seek to about 2:00, and confirm the time changes. Check that the step thumbnails load. Tap a step and record whether the video jumps to that moment (K4).
3. Practise: upload `tracks/cases/origami-crane/samples/flawed.mp4` as "your attempt". Use `browser_file_upload` after clicking the upload control, or `browser_run_code` with `page.setInputFiles`. Record the wait and the progress messages. This may use live AI calls; log them.
4. Read the feedback on the phone. Is the first divergence shown with a frame from your video and the matching moment in the source? Can the side-by-side videos (if any) be used at 375 px?
5. Retry with `good.mp4`. Results on the phone.
6. Upload `unrelated.mp4` once as an attempt. Does the app explain kindly that this doesn't look like the task, rather than score it?
7. End-of-walk answers.

### 6.3 W3: learner, Tabla (audio)
**Persona:** Meera, a music teacher. Desktop.
1. Open the tabla skill from the library. Check that the source audio plays and that the beat timeline or visual makes sense to a non-programmer.
2. Practise:
   - If the app offers recording, note what it asks for, but **don't** record (there is no microphone).
   - Upload `tracks/cases/tabla/samples/flawed.wav`, then retry with `good.wav`.
   - Upload `unrelated.wav` once.
3. Judge whether audio feedback is understandable without seeing a waveform. Is "can't tell" honesty present where it should be (K6)?
4. End-of-walk answers.

### 6.4 W4: creator (share a skill)
**Persona:** Lakshmi, 58, a kolam artist who wants her pattern taught, with credit. Not technical. Desktop, then repeat step 2 on phone.
1. From the home page, find how to share a skill, **without** using the URL. Record how many clicks it takes and whether it is clear what you need and what rights you must have.
2. In the composer:
   - Upload `tracks/samples/sources/kolam_photo.png` as the source. If the composer offers built-in example sources, try one too.
   - Record every step, message and wait.
   - On the "what the AI understood" or proposal step: are the steps and checks understandable? Can she edit or remove a step (K2)? Is it clear what is AI-inferred and what is observed?
   - Finish creating the skill.
3. Go to **My skills**. Is the new skill there with a clear status ("not yet checked by an expert", "sent for review")? Send it for review, and record the confirmation copy.
4. Open the creator's own skill page and the insights. Do the empty states teach (product brief §3.6)?
5. Repeat step 2 with the audio source `tracks/cases/tabla/samples/good.wav`, as a "new rhythm".
6. Try one **bad** upload: a `.json` file such as `tracks/cases/tabla/samples/samples.json`. Does the error say what to do next?
7. End-of-walk answers.

### 6.5 W5: steward
**Persona:** Dr. Rao, who runs a community heritage archive. Desktop.
1. Find the steward entry **from the UI**. Sign in with the code `local-test-code`. Check that a wrong code first gives a clear error.
2. Go through each tab: Overview, Review queue, Library, Consent/licences, Insights, Usage. For each one, record: purpose clear? empty state teaches? numbers believable? any jargon?
3. Open W4's skill in the queue. Review it, approve and publish it, and record each confirmation. Try "reject" or "hide" on a different item if one exists; cancel at the confirmation.
4. Usage: compare the server's call count with `live-calls.md`.
5. As a learner, in a **new** context, check that the published skill appears in the library and can be practised. Do one practice with `tracks/samples/sources/kolam_photo.png` as the attempt, if the skill accepts photos.
6. End-of-walk answers.

### 6.6 Files allowed for uploads
| File | Use |
|---|---|
| `tracks/cases/origami-crane/samples/good.mp4`, `flawed.mp4`, `unrelated.mp4` | crane attempts |
| `tracks/cases/tabla/samples/good.wav`, `flawed.wav`, `unrelated.wav` | tabla attempts; composer audio source |
| `tracks/samples/sources/kolam_photo.png` | composer image source; kolam photo attempt |
| `tracks/cases/kolam/source/ithayakkamalam_target.jpg` | kolam photo attempt (should score well) |
| `tracks/track-b/eval/kolam/synthetic/raster_missing_stage_rotated/attempt.png` | kolam photo attempt (flawed) |
| `tracks/cases/tabla/samples/samples.json` | a deliberately wrong file type |

### 6.7 W6: navigation, the "How we check" page, edge cases, robustness
Desktop.
1. **Header and navigation:** visit every header item. Is the active state clear? Do the names match the page titles? Does the logo go home?
2. **"How we check" / evidence page:** would a technical judge trust it? Are the numbers sourced? Is it readable by a non-technical judge? Does it surface K5 and K9 without fluff?
3. **"What the labels mean"** and "How it works": accurate against what you saw in W1–W5?
4. **Settings and the own-key dialog:** open them (no key entered). Is the copy clear about why a key is optional and where it is stored?
5. Deep links:
   - Open `/?view=practice&case=tabla` and `/?view=transmission&case=kolam` directly in a fresh context.
   - Open an unknown case, `/?view=source&case=nope`.
   - Open `/?view=steward` while signed out.
   - Record what happens.
6. Double-click submit buttons. Upload during an upload. Navigate away mid-wait and come back.
7. Throttle the network with `browser_run_code`: create a CDP session, then call `Network.emulateNetworkConditions` with latency 400, downloadThroughput 50000 and uploadThroughput 20000. Load the home page and a Learn page. Are the loading states graceful? Turn throttling off afterwards.
8. **Synthetic showcase cases** (bicycle repair, handloom, micrometer, square knot; reached via "Design archetypes" or the library):
   - Are they clearly labelled as made-up examples?
   - Do they look like part of the product, or like leftovers?
   - Would a judge be confused that they can't be practised?

### 6.8 W7: accessibility and visual quality sweep
1. **Keyboard only** (desktop): from `/`, use Tab, Shift+Tab, Enter, Space and Esc. Go library → Kolam Learn → Practise → (use a sample attempt) → Results. Record any place where focus is invisible or lost, or something can't be reached. Dialogs must trap focus and close on Esc.
2. **Phone 375 px:** for every view in §6.0, record any horizontal scroll, overlap or text cut-off.
3. **Text size and contrast:**
   - Run `browser_evaluate` to list elements whose computed font size is under 12 px, with a text sample. Ignore icons.
   - Check contrast by eye on the amber, cyan and crimson text on dark backgrounds, and record any that look faint.
4. **Visual coherence:**
   - Across all screens, judge whether they look like one product: type scale, spacing, card styles, button styles and icon set.
   - List screens that look like a different app or an older version.
5. **Dark/light:** if the app has only one theme, note it (no action). If it follows `prefers-color-scheme`, check both.

## 7. Static checks (branch `static`, no browser; can run while the walks run)

### S1: copy and content inventory
1. Extract every user-visible string in `app/src` with `rg`. The copy lives mostly in `app/src/copy/plain.ts` and the components. Skip `api/mock/` and test scripts. Write a table to `obs\S1-strings.md`: `file:line | text | role who sees it`. Cap it at 600 rows, prioritising learner screens.
2. Flag (as `S1-nn` observations):
   - terms from the product brief §5 "never show" list;
   - marketing superlatives ("revolutionary", "seamless", "powerful", "cutting-edge", "unlock", "empower", "harness", "leverage");
   - "nobody does this" style claims;
   - em-dash-heavy or triple-adjective AI-style prose;
   - the same explanation repeated in several places (quote each place);
   - inconsistent terms (practise/practice, skill/case, try/attempt, source/demonstration);
   - US/UK spelling mixes;
   - placeholder or test text.
3. Run `npm --prefix app run check:plain` and `npm --prefix app run check:roles`. Set `ANVESHAN_STEWARD_CODE=local-test-code` in that shell. Both need the service on 8080, which setup started. Record the summary lines and every failure.

### S2: claims versus reality
1. Read `README.md`, the home page and "How it works" copy (from `app/src/copy/plain.ts`), and `docs/product/novelty-boundary.md` (positioning).
2. List every claim the app or README makes about what it does. Examples: "a phone is enough", "every tip links to the source", "pressure isn't measured", "scores come from fixed rules", "saved as a record", "works for any skill".
3. Mark each claim:
   - `verified` (cite a W-observation or a test file);
   - `partly` (say what is missing);
   - `not seen`.
   Claims will be cross-checked against the walk files once they exist; write `pending W<n>` until then and fill them in at the end of S3.
4. Check that the README quick start works as written: read it, and run only the non-destructive commands (`pytest`, `build`). Record any step that is wrong or out of date.
5. Write `obs\S2.md`, with a claims table and observations.

### S3: technical health
1. Run `.venv\Scripts\python -m pytest tracks/common/tests tracks/track-a/tests tracks/track-b/tests service/tests -m "not live" -q`, piped through `| Select-Object -Last 15`. Record the counts and any failures.
2. Run `.venv\Scripts\python tools/smoke_deployed.py http://localhost:8080 --insecure`, with `ANVESHAN_SMOKE_STEWARD_CODE=local-test-code`. Record the result.
3. Time `GET` on `/`, `/api/cases`, each case's media and each sample, with `curl.exe -s -o NUL -w "%{http_code} %{size_download} %{time_total}"`. Flag anything over 1.5 s locally, or over 5 MB that a first visit loads.
4. Built bundle: record the size of `app/dist/assets/*.js`. Flag a JS bundle over 1 MB.
5. Scan `logs\service.log` (after the walks finish, or at the end) for tracebacks, 5xx responses and warnings. Quote the first line of each distinct one.
6. Finally, go back to `obs\S2.md` and replace each `pending W<n>` with the verdict, once the walk files exist. If the walks are not yet done, the jury step does this.
7. Write `obs\S3.md`.

## 8. Jury and compile

### 8.1 Jury step (after both branches finish)
Read every `obs\*.md` file. Look at the screenshots behind S0 and S1 observations. Write `.kiro\k10-run\JURY.md`. Four judges and three first-time users each write a short verdict **based only on the observations**; cite IDs and make no new claims.

| Voice | Focus |
|---|---|
| J1 Google Cloud engineer | Technical merit and Gen AI (40%): is Gemini used meaningfully? is it sound, scalable and deployed? |
| J2 Social-impact and heritage judge | Problem alignment and impact (25%): does this help real people pass on a physical skill? |
| J3 Innovation judge (a sceptic: "isn't this a wrapper around Gemini?") | Originality (25%): which key ideas K1–K9 convinced, and which were invisible or oversold |
| J4 Product designer | UX (10%): usability, accessibility, cohesion |
| U1 Priya (learner), U2 Lakshmi (creator), U3 Dr. Rao (steward) | Could I use it? What did I get? Would I come back? |

Each judge gives:
- a score out of 10 for their criterion;
- the three observations that cost the most points;
- the one change that would raise the score most.

Then add:
- a **key ideas table**: K1–K9 × {visible?, understood?, overdone?, best place it shows, observation IDs};
- **"Feels like an afterthought or AI filler"**: every such observation, grouped by screen;
- **"Delights, keep these"**: the `delight` observations.

### 8.2 Compile step: `.kiro\k10-run\REPORT.md` (the hand-off to Claude Code)
1. **Header:** commit, date, build result, test counts, live calls used.
2. **Totals:** observations by severity × category.
3. **All S0 and S1**, sorted by severity and then by screen, as full blocks copied from the `obs` files. Merge duplicates (keep one, list the others under `also:`).
4. **S2 and S3:** one line each (`ID · severity · category · where · one-line saw`).
5. **Per-screen index:** screen → observation IDs → screenshot files.
6. **Jury summary:** the scores table and the top 10 changes by expected score gain, citing IDs.
7. **Claims table** (from S2, with verdicts filled in).
8. **First-impression answers** from every walk, side by side.
9. **Open questions** for Claude Code: things Kiro could not decide.

Then update `STATUS.md` to all `DONE`. Call `send_message` (success) with: "K10 done: REPORT.md has N observations (S0 a, S1 b, S2 c, S3 d)." Leave the service running.

## 9. Defaults when unsure (log each use in `obs\<STEP>.md` under "Decisions")
1. If the spec and the screen disagree, observe the screen and record the difference.
2. If you can't tell whether something is a bug or intended, record it with `confidence: low`.
3. If the app asks for a key, a payment or a sign-in other than the steward code, don't proceed. Record it and take the no-key path.
4. If live calls reach 40, stop doing uploads that call the AI. Use the "sample attempt" buttons instead, and note this.
5. If a step can't finish within 75 minutes, write what you have, mark the step `DONE (partial)`, and continue.

## 10. Manual fallback (if workflows are unavailable)
In the parent chat, run in this order: setup (§3), W1 to W7 (§6), S1 to S3 (§7), jury (§8.1), compile (§8.2). Write the same files.
