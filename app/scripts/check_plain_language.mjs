/**
 * check_plain_language.mjs
 *
 * Plain-language scan: walk the mock app and report any banned learner terms visible
 * in the learner/creator surfaces. Exits 1 when findings exist, 0 otherwise.
 *
 * Usage:
 *   node scripts/check_plain_language.mjs [--self-test]
 *   ANVESHAN_URL=http://localhost:5174 node scripts/check_plain_language.mjs
 */

import puppeteer from 'puppeteer-core';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// ---------------------------------------------------------------------------
// Config
// ---------------------------------------------------------------------------

const CHROME_PATH =
  process.env.CHROME_PATH ||
  (process.platform === 'win32'
    ? 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
    : '/usr/bin/google-chrome');

const BASE_URL = process.env.ANVESHAN_URL || 'http://localhost:5174';
const SCREENSHOT_DIR = path.resolve(__dirname, '../../var/k9-screens');

const STEP_TIMEOUT = 10_000; // 10 s per wait

// ---------------------------------------------------------------------------
// Load BANNED_LEARNER_TERMS from plain.ts at runtime (no TS import)
// ---------------------------------------------------------------------------

function loadBannedTerms() {
  const tsPath = path.resolve(__dirname, '../src/copy/plain.ts');
  const src = fs.readFileSync(tsPath, 'utf8');
  // Match the array literal inside BANNED_LEARNER_TERMS: string[] = [ ... ];
  const m = src.match(/BANNED_LEARNER_TERMS\s*:\s*string\[\]\s*=\s*\[([\s\S]*?)\];/);
  if (!m) throw new Error('Cannot locate BANNED_LEARNER_TERMS in plain.ts');
  const block = m[1];
  // Extract all string literals
  const terms = [];
  const re = /'([^']+)'|"([^"]+)"/g;
  let hit;
  while ((hit = re.exec(block)) !== null) {
    terms.push(hit[1] ?? hit[2]);
  }
  return terms;
}

// ---------------------------------------------------------------------------
// Term matching (mirrors the rule in plain.ts JSDoc)
// ---------------------------------------------------------------------------

function buildMatcher(terms) {
  return terms.map((term) => {
    const caseSensitive = /[A-Z]/.test(term);
    // word boundaries when term starts/ends with a word character
    const leftBound = /^\w/.test(term) ? '\\b' : '';
    const rightBound = /\w$/.test(term) ? '\\b' : '';
    const escaped = term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const flags = caseSensitive ? 'g' : 'gi';
    return { term, re: new RegExp(`${leftBound}${escaped}${rightBound}`, flags) };
  });
}

// ---------------------------------------------------------------------------
// Self-test mode
// ---------------------------------------------------------------------------

function runSelfTest(terms) {
  const matchers = buildMatcher(terms);
  // HTML containing CLM-01, "satisfied", and a data-plain-exempt "claim"
  const html = `<body>
    <p>This text has CLM-01 in it and satisfied as a status.</p>
    <span data-plain-exempt>claim should be ignored here</span>
  </body>`;

  // Simulate visible text extraction (exempt nodes stripped)
  // Parse exempt text by removing data-plain-exempt subtrees (simple regex for self-test)
  const exemptStripped = html.replace(/<[^>]+data-plain-exempt[^>]*>[\s\S]*?<\/[^>]+>/g, '');
  const plainText = exemptStripped.replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim();

  const findings = [];
  for (const { term, re } of matchers) {
    re.lastIndex = 0;
    const match = re.exec(plainText);
    if (match) {
      const start = Math.max(0, match.index - 20);
      const end = Math.min(plainText.length, match.index + term.length + 20);
      findings.push({ term, snippet: plainText.slice(start, end).trim() });
    }
  }

  const foundTerms = findings.map((f) => f.term);
  const expectFound = ['CLM-'];
  const expectMissed = ['claim']; // inside data-plain-exempt

  let ok = true;
  for (const expected of expectFound) {
    const hit = foundTerms.some((t) => t === expected);
    if (!hit) {
      console.error(`SELF-TEST FAIL: expected to find "${expected}" but did not`);
      ok = false;
    }
  }
  for (const shouldMiss of expectMissed) {
    const hit = foundTerms.some((t) => t === shouldMiss);
    if (hit) {
      console.error(`SELF-TEST FAIL: found "${shouldMiss}" but it should be exempt`);
      ok = false;
    }
  }

  if (ok) {
    console.log('SELF-TEST PASS: CLM-01 found, exempt "claim" not found');
    process.exit(0);
  } else {
    process.exit(1);
  }
}

// ---------------------------------------------------------------------------
// Page scan
// ---------------------------------------------------------------------------

async function scan(page, label, matchers) {
  const findings = await page.evaluate((terms) => {
    const results = [];

    // Walk visible text nodes, skipping data-plain-exempt subtrees,
    // hidden elements (offsetParent === null, except body), script and style.
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, {
      acceptNode(node) {
        let el = node.parentElement;
        while (el && el !== document.body) {
          if (el.dataset && el.dataset.plainExempt !== undefined) return NodeFilter.FILTER_REJECT;
          const tag = el.tagName && el.tagName.toLowerCase();
          if (tag === 'script' || tag === 'style') return NodeFilter.FILTER_REJECT;
          if (el !== document.body && el.offsetParent === null) return NodeFilter.FILTER_REJECT;
          el = el.parentElement;
        }
        return NodeFilter.FILTER_ACCEPT;
      },
    });

    const textParts = [];
    let node;
    while ((node = walker.nextNode())) {
      const t = node.nodeValue || '';
      if (t.trim()) textParts.push(t);
    }
    const fullText = textParts.join(' ');

    for (const { term, caseSensitive, pattern } of terms) {
      const flags = caseSensitive ? 'g' : 'gi';
      const re = new RegExp(pattern, flags);
      let match;
      while ((match = re.exec(fullText)) !== null) {
        const start = Math.max(0, match.index - 30);
        const end = Math.min(fullText.length, match.index + term.length + 30);
        results.push({ term, snippet: fullText.slice(start, end).trim() });
        break; // one hit per term per scan
      }
    }
    return results;
  }, matchers.map(({ term, re }) => ({
    term,
    caseSensitive: /[A-Z]/.test(term),
    pattern: re.source,
  })));

  return findings.map((f) => ({ label, ...f }));
}

// ---------------------------------------------------------------------------
// Screenshot helper
// ---------------------------------------------------------------------------

async function shot(page, name) {
  fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
  const p = path.join(SCREENSHOT_DIR, `${name}.png`);
  await page.screenshot({ path: p, fullPage: true });
}

// ---------------------------------------------------------------------------
// Main walk
// ---------------------------------------------------------------------------

async function runWalk(matchers) {
  const browser = await puppeteer.launch({
    executablePath: CHROME_PATH,
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--window-size=1280,900'],
    defaultViewport: { width: 1280, height: 900 },
  });

  const allFindings = [];
  let debugOk = true;
  let stewardOk = true;

  try {
    const page = await browser.newPage();
    page.setDefaultTimeout(STEP_TIMEOUT);
    page.setDefaultNavigationTimeout(STEP_TIMEOUT * 3);

    // ── Step 1: Library ──────────────────────────────────────────────────────
    console.log('  Step 1: Library');
    await page.goto(BASE_URL, { waitUntil: 'networkidle0', timeout: 30_000 });
    allFindings.push(...await scan(page, '1-library', matchers));
    await shot(page, '1-library');

    // ── Step 2: Kolam → Learn ────────────────────────────────────────────────
    console.log('  Step 2: Kolam → Learn');
    // Click the first "Start" button for the Kolam skill card
    await clickByText(page, ['Start', 'Kolam', 'Learn'], '2-kolam-learn');
    await page.waitForNetworkIdle({ timeout: STEP_TIMEOUT }).catch(() => {});
    allFindings.push(...await scan(page, '2-kolam-learn', matchers));
    await shot(page, '2-kolam-learn');

    // ── Step 3: Practise ─────────────────────────────────────────────────────
    console.log('  Step 3: Practise');
    await clickByText(page, ['Start practising', 'Practise'], '3-practise');
    await page.waitForNetworkIdle({ timeout: STEP_TIMEOUT }).catch(() => {});
    // Try "Try a sample attempt" button first (added by P2), else upload fixture
    const trySampleBtn = await findButtonByText(page, 'Try a sample attempt');
    if (trySampleBtn) {
      console.log('    Using "Try a sample attempt" button (P2)');
      await trySampleBtn.click();
    } else {
      console.log('    "Try a sample attempt" not found — uploading PNG fixture');
      // Create PNG fixture if it doesn't exist
      await ensureFixturePng();
      const input = await page.$('input[type=file]');
      if (input) {
        const fixturePath = path.resolve(__dirname, 'fixtures/attempt.png');
        await input.uploadFile(fixturePath);
      }
    }
    await page.waitForNetworkIdle({ timeout: STEP_TIMEOUT * 3 }).catch(() => {});
    allFindings.push(...await scan(page, '3-practise', matchers));
    await shot(page, '3-practise');

    // ── Step 4: First-try result; open "Why this feedback?" disclosures ───────
    console.log('  Step 4: First-try results');
    await page.waitForNetworkIdle({ timeout: STEP_TIMEOUT * 2 }).catch(() => {});
    // Open all "Why this feedback?" disclosures
    await page.evaluate(() => {
      document.querySelectorAll('summary, button, details').forEach((el) => {
        const txt = el.textContent || '';
        if (txt.toLowerCase().includes('why this feedback')) {
          if (el.tagName === 'SUMMARY') {
            const details = el.closest('details');
            if (details && !details.open) details.open = true;
          } else {
            el.click();
          }
        }
      });
    });
    await delay(500);
    allFindings.push(...await scan(page, '4-first-result', matchers));
    await shot(page, '4-first-result');

    // ── Step 5: Second try → Results ─────────────────────────────────────────
    console.log('  Step 5: Second try');
    const trySample2 = await findButtonByText(page, 'Try a sample attempt');
    if (trySample2) {
      await trySample2.click();
    } else {
      const input2 = await page.$('input[type=file]');
      if (input2) {
        const fixturePath = path.resolve(__dirname, 'fixtures/attempt.png');
        await input2.uploadFile(fixturePath);
      }
    }
    await page.waitForNetworkIdle({ timeout: STEP_TIMEOUT * 3 }).catch(() => {});
    allFindings.push(...await scan(page, '5-second-try-results', matchers));
    await shot(page, '5-second-try-results');

    // ── Step 6: Tabla → Learn ────────────────────────────────────────────────
    console.log('  Step 6: Tabla → Learn');
    await page.goto(BASE_URL, { waitUntil: 'networkidle0', timeout: 30_000 });
    await clickByText(page, ['Tabla', 'Start', 'Learn'], '6-tabla-learn');
    await page.waitForNetworkIdle({ timeout: STEP_TIMEOUT }).catch(() => {});
    allFindings.push(...await scan(page, '6-tabla-learn', matchers));
    await shot(page, '6-tabla-learn');

    // ── Step 7: Composer ──────────────────────────────────────────────────────
    console.log('  Step 7: Composer');
    await page.goto(`${BASE_URL}?view=composer`, { waitUntil: 'networkidle0', timeout: 30_000 });
    await page.waitForNetworkIdle({ timeout: STEP_TIMEOUT }).catch(() => {});
    // Upload fixture in the composer
    const compInput = await page.$('input[type=file]');
    if (compInput) {
      await ensureFixturePng();
      const fixturePath = path.resolve(__dirname, 'fixtures/attempt.png');
      await compInput.uploadFile(fixturePath);
      await page.waitForNetworkIdle({ timeout: STEP_TIMEOUT * 3 }).catch(() => {});
    }
    allFindings.push(...await scan(page, '7-composer-upload', matchers));
    await shot(page, '7-composer-upload');
    // Try to advance through wizard
    const createBtn = await findButtonByText(page, ['Create', 'Proposal', 'Looks right']);
    if (createBtn) {
      await createBtn.click();
      await page.waitForNetworkIdle({ timeout: STEP_TIMEOUT * 2 }).catch(() => {});
      allFindings.push(...await scan(page, '7-composer-proposal', matchers));
      await shot(page, '7-composer-proposal');
    }
    // Check steps dialog
    const checkStepsBtn = await findButtonByText(page, 'Check steps');
    if (checkStepsBtn) {
      await checkStepsBtn.click();
      await delay(500);
      allFindings.push(...await scan(page, '7-check-steps-dialog', matchers));
      await shot(page, '7-check-steps-dialog');
      // Close dialog
      const closeBtn = await page.$('[role="dialog"] button[aria-label*="lose"], [role="dialog"] button[aria-label*="Close"]');
      if (closeBtn) await closeBtn.click();
      else await page.keyboard.press('Escape');
      await delay(300);
    }

    // ── Step 8: My skills ─────────────────────────────────────────────────────
    console.log('  Step 8: My skills');
    await page.goto(`${BASE_URL}?view=mine`, { waitUntil: 'networkidle0', timeout: 30_000 });
    await page.waitForNetworkIdle({ timeout: STEP_TIMEOUT }).catch(() => {});
    allFindings.push(...await scan(page, '8-my-skills', matchers));
    await shot(page, '8-my-skills');

    // ── Debug sanity check ────────────────────────────────────────────────────
    console.log('  Debug sanity check: ?debug=1&view=source&case=kolam');
    await page.goto(`${BASE_URL}?debug=1&view=source&case=kolam`, { waitUntil: 'networkidle0', timeout: 30_000 });
    await page.waitForNetworkIdle({ timeout: STEP_TIMEOUT }).catch(() => {});
    const bodyText = await page.$eval('body', (el) => el.innerText);
    debugOk = bodyText.includes('CLM-');
    if (!debugOk) {
      console.warn('  WARNING: debug view does not contain "CLM-" — debug view may be broken');
    } else {
      console.log('  Debug view OK (contains CLM-)');
    }
    // Do NOT scan debug view
    await shot(page, 'debug-sanity');

    // ── Steward console: exempt from scan ─────────────────────────────────────
    console.log('  Steward console: sign in with code "steward", assert Overview');
    await page.goto(`${BASE_URL}?view=steward`, { waitUntil: 'networkidle0', timeout: 30_000 });
    await page.waitForNetworkIdle({ timeout: STEP_TIMEOUT }).catch(() => {});
    // Enter steward code
    const codeInput = await page.$('input[type="password"], input[name*="code"], input[placeholder*="code"]');
    if (codeInput) {
      await codeInput.type('steward');
      const signInBtn = await findButtonByText(page, 'Sign in');
      if (signInBtn) {
        await signInBtn.click();
        await page.waitForNetworkIdle({ timeout: STEP_TIMEOUT }).catch(() => {});
      }
    }
    const stewardBody = await page.$eval('body', (el) => el.innerText).catch(() => '');
    stewardOk = stewardBody.toLowerCase().includes('steward console');
    if (!stewardOk) {
      console.warn('  WARNING: steward console body does not contain "Steward console"');
    } else {
      console.log('  Steward console OK');
    }
    // Do NOT scan steward console
    await shot(page, 'steward-console');

  } finally {
    await browser.close();
  }

  return { allFindings, debugOk, stewardOk };
}

// ---------------------------------------------------------------------------
// Utility: click the first button/link matching one of the text strings
// ---------------------------------------------------------------------------

async function clickByText(page, texts, label) {
  const list = Array.isArray(texts) ? texts : [texts];
  for (const text of list) {
    const clicked = await page.evaluate((needle) => {
      const el = Array.from(document.querySelectorAll('button, a, [role=button]'))
        .find((e) => e.textContent && e.textContent.includes(needle));
      if (el) { el.click(); return true; }
      return false;
    }, text);
    if (clicked) return;
  }
  console.warn(`  Could not click any of [${list.join(', ')}] for step ${label}`);
}

async function findButtonByText(page, texts) {
  const list = Array.isArray(texts) ? texts : [texts];
  for (const text of list) {
    const el = await page.evaluateHandle((needle) => {
      return Array.from(document.querySelectorAll('button, a, [role=button]'))
        .find((e) => e.textContent && e.textContent.includes(needle)) || null;
    }, text);
    if (el && (await el.evaluate((e) => e !== null))) {
      const box = await el.boundingBox();
      if (box) return el;
    }
  }
  return null;
}

function delay(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

// ---------------------------------------------------------------------------
// Ensure PNG fixture exists
// ---------------------------------------------------------------------------

async function ensureFixturePng() {
  const dir = path.resolve(__dirname, 'fixtures');
  const p = path.join(dir, 'attempt.png');
  if (fs.existsSync(p)) return;
  fs.mkdirSync(dir, { recursive: true });
  // Minimal 1×1 white PNG (89 bytes)
  const minimalPng = Buffer.from(
    '89504e470d0a1a0a0000000d49484452000000010000000108020000009001' +
    '2e00000000c4944415478016360f8ff0f00000200016c3c3f00000000049454' +
    '4e44ae426082',
    'hex'
  );
  fs.writeFileSync(p, minimalPng);
  console.log(`  Created minimal PNG fixture: ${p}`);
}

// ---------------------------------------------------------------------------
// Entry point
// ---------------------------------------------------------------------------

async function main() {
  const selfTest = process.argv.includes('--self-test');

  let terms;
  try {
    terms = loadBannedTerms();
  } catch (err) {
    console.error('Failed to load BANNED_LEARNER_TERMS:', err.message);
    process.exit(1);
  }

  console.log(`Loaded ${terms.length} banned terms from plain.ts`);

  if (selfTest) {
    runSelfTest(terms);
    return; // runSelfTest calls process.exit
  }

  const matchers = buildMatcher(terms);
  console.log(`\nPlain-language scan — ${BASE_URL}`);

  const { allFindings, debugOk, stewardOk } = await runWalk(matchers);

  // Print findings table
  console.log(`\n${'='.repeat(70)}`);
  console.log('  ' + 'Step'.padEnd(28) + ' ' + 'Term'.padEnd(23) + ' Snippet');
  console.log('-'.repeat(70));
  if (allFindings.length === 0) {
    console.log('  (no findings)');
  } else {
    for (const f of allFindings) {
      console.log(`  ${f.label.padEnd(28)} ${f.term.padEnd(23)} …${f.snippet}…`);
    }
  }
  console.log('='.repeat(70));
  console.log(`Debug view contains CLM-: ${debugOk ? 'yes ✓' : 'NO ✗'}`);
  console.log(`Steward console renders:  ${stewardOk ? 'yes ✓' : 'NO ✗'}`);
  console.log(`Total findings: ${allFindings.length}`);
  console.log(`Screenshots saved to: ${SCREENSHOT_DIR}`);

  if (allFindings.length > 0 || !debugOk || !stewardOk) {
    process.exit(1);
  }
  process.exit(0);
}

main().catch((err) => {
  console.error('Fatal error:', err);
  process.exit(1);
});
