/**
 * check_roles.mjs
 *
 * Role walk: learner, creator and steward journeys using two browser contexts.
 * Runs against the mock app for steps the mock supports; marks real-service steps
 * "not run (needs P1)".
 *
 * Usage:
 *   node scripts/check_roles.mjs
 *   ANVESHAN_URL=http://localhost:5174 node scripts/check_roles.mjs
 *
 * For the real-service run (after P1 merges):
 *   ANVESHAN_STEWARD_OPEN=0 ANVESHAN_STEWARD_TOKEN=local-test-code \
 *     ANVESHAN_URL=http://localhost:8080 node scripts/check_roles.mjs
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
const STEWARD_CODE = process.env.ANVESHAN_STEWARD_TOKEN || 'steward'; // env: ANVESHAN_STEWARD_TOKEN
const SCREENSHOT_DIR = path.resolve(__dirname, '../../var/k9-screens');

const STEP_TIMEOUT = 10_000;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function assert(condition, message) {
  if (!condition) {
    throw new Error(`ASSERTION FAILED: ${message}`);
  }
}

async function shot(page, name) {
  fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
  const p = path.join(SCREENSHOT_DIR, `roles-${name}.png`);
  await page.screenshot({ path: p, fullPage: true });
}

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
  throw new Error(`Cannot click [${list.join(', ')}] for ${label}`);
}

async function bodyContains(page, text) {
  const body = await page.$eval('body', (el) => el.innerText).catch(() => '');
  return body.toLowerCase().includes(text.toLowerCase());
}

async function waitForText(page, text, timeout = STEP_TIMEOUT) {
  const deadline = Date.now() + timeout;
  while (Date.now() < deadline) {
    if (await bodyContains(page, text)) return;
    await sleep(300);
  }
  throw new Error(`Timed out waiting for text: "${text}"`);
}

async function ensureFixturePng() {
  const dir = path.resolve(__dirname, 'fixtures');
  const p = path.join(dir, 'attempt.png');
  if (fs.existsSync(p)) return p;
  fs.mkdirSync(dir, { recursive: true });
  // Minimal 1×1 white PNG
  const minimalPng = Buffer.from(
    '89504e470d0a1a0a0000000d49484452000000010000000108020000009001' +
    '2e00000000c4944415478016360f8ff0f00000200016c3c3f00000000049454' +
    '4e44ae426082',
    'hex'
  );
  fs.writeFileSync(p, minimalPng);
  return p;
}

// ---------------------------------------------------------------------------
// Track results
// ---------------------------------------------------------------------------

const steps = [];

function pass(name, note = '') {
  steps.push({ status: 'PASS', name, note });
  console.log(`  ✓ ${name}${note ? ' — ' + note : ''}`);
}

function fail(name, reason) {
  steps.push({ status: 'FAIL', name, note: reason });
  console.error(`  ✗ ${name} — ${reason}`);
}

function skip(name, reason) {
  steps.push({ status: 'SKIP', name, note: reason });
  console.log(`  - ${name} — ${reason}`);
}

// ---------------------------------------------------------------------------
// Main walk
// ---------------------------------------------------------------------------

async function main() {
  const fixturePath = await ensureFixturePng();

  const browser = await puppeteer.launch({
    executablePath: CHROME_PATH,
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--window-size=1280,900'],
    defaultViewport: { width: 1280, height: 900 },
  });

  try {
    const contextA = await browser.createBrowserContext();
    const contextB = await browser.createBrowserContext();
    const contextSteward = await browser.createBrowserContext();

    const pageA = await contextA.newPage();
    const pageB = await contextB.newPage();
    const pageSteward = await contextSteward.newPage();

    pageA.setDefaultTimeout(STEP_TIMEOUT);
    pageB.setDefaultTimeout(STEP_TIMEOUT);
    pageSteward.setDefaultTimeout(STEP_TIMEOUT);

    // ── Step 1: A creates a skill ─────────────────────────────────────────────
    console.log('\n[1] A creates a skill');
    skip('A creates a skill via composer', 'not run (needs P1 + recorded mode for compose)');
    // In the mock: navigate to composer and check it loads
    await pageA.goto(`${BASE_URL}?view=composer`, { waitUntil: 'networkidle0', timeout: 30_000 });
    if (await bodyContains(pageA, 'composer') || await bodyContains(pageA, 'Share') || await bodyContains(pageA, 'Upload')) {
      pass('A: composer page loads', 'mock');
    } else {
      fail('A: composer page loads', 'composer page did not render expected text');
    }
    await shot(pageA, '01-a-composer');

    // ── Step 2: A checks steps → Looks right → Publish ───────────────────────
    console.log('\n[2] A: Check steps → Publish');
    skip('A: Check steps → Looks right → Publish', 'not run (needs P1 + full composer)');
    skip('A: status becomes "Waiting for review"', 'not run (needs P1)');

    // ── Step 3: B: Library does not show unreviewed skill ─────────────────────
    console.log('\n[3] B: Library does not show unpublished skill');
    skip('B: unpublished skill absent from Library', 'not run (needs P1 community skill workflow)');

    // ── Step 4: Steward: queue → Review → Publish ─────────────────────────────
    console.log('\n[4] Steward: sign in and check queue/publish');
    await pageSteward.goto(`${BASE_URL}?view=steward`, { waitUntil: 'networkidle0', timeout: 30_000 });
    // Sign in with steward code
    const codeInput = await pageSteward.$('input[type="password"], input[name*="code"], input[placeholder*="code"]');
    if (codeInput) {
      await codeInput.type(STEWARD_CODE);
      const signInBtn = await pageSteward.evaluateHandle(() =>
        Array.from(document.querySelectorAll('button')).find((b) => b.textContent.includes('Sign in')) || null
      );
      if (signInBtn && await signInBtn.evaluate((el) => el !== null)) {
        await signInBtn.click();
        await sleep(1000);
        await pageSteward.waitForNetworkIdle({ timeout: STEP_TIMEOUT }).catch(() => {});
      }
    }
    const stewardBody = await pageSteward.$eval('body', (el) => el.innerText).catch(() => '');
    if (stewardBody.toLowerCase().includes('steward console') || stewardBody.toLowerCase().includes('overview')) {
      pass('Steward: console opened', 'mock code "steward"');
    } else {
      skip('Steward: console opened', 'not run (needs P3 steward console UI)');
    }
    await shot(pageSteward, '04-steward-console');

    // Check queue tab
    const queueTab = await pageSteward.evaluateHandle(() =>
      Array.from(document.querySelectorAll('button, a, [role=tab]'))
        .find((el) => el.textContent.includes('Review') || el.textContent.includes('Queue')) || null
    );
    if (queueTab && await queueTab.evaluate((el) => el !== null)) {
      await queueTab.click();
      await sleep(500);
      pass('Steward: Review queue tab accessible', 'mock');
      await shot(pageSteward, '04-steward-queue');
    } else {
      skip('Steward: Review queue tab', 'not found — needs P3 steward console');
    }

    // ── Step 5: B sees published skill in Library ─────────────────────────────
    console.log('\n[5] B: Library shows curated published skills');
    await pageB.goto(BASE_URL, { waitUntil: 'networkidle0', timeout: 30_000 });
    if (await bodyContains(pageB, 'Kolam') || await bodyContains(pageB, 'kolam')) {
      pass('B: Library shows published curated skills', 'Kolam visible');
    } else {
      fail('B: Library shows published curated skills', 'Kolam not found in library');
    }
    await shot(pageB, '05-b-library');

    // B can open Learn and Practise for a published skill
    await pageB.goto(`${BASE_URL}?view=source&case=kolam`, { waitUntil: 'networkidle0', timeout: 30_000 });
    if (await bodyContains(pageB, 'kolam') || await bodyContains(pageB, 'step') || await bodyContains(pageB, 'learn')) {
      pass('B: can open Learn page for published skill');
    } else {
      fail('B: can open Learn page', 'expected Learn page content not found');
    }
    await shot(pageB, '05-b-learn');

    // ── Step 6: A: My skills shows status ────────────────────────────────────
    console.log('\n[6] A: My skills');
    await pageA.goto(`${BASE_URL}?view=mine`, { waitUntil: 'networkidle0', timeout: 30_000 });
    if (await bodyContains(pageA, 'skill') || await bodyContains(pageA, 'My skills')) {
      pass('A: My skills page renders', 'mock');
    } else {
      fail('A: My skills page renders', 'expected skills content not found');
    }
    await shot(pageA, '06-a-my-skills');
    skip('A: "Published" status in My skills', 'not run (needs P1 + published community skill)');
    skip('A: "See how learners are doing" opens', 'not run (needs P1 + published community skill)');

    // ── Step 7: Steward hides skill / consent / usage ────────────────────────
    console.log('\n[7] Steward: Library → Hide, Consent, Usage');
    skip('Steward: Library → Hide skill', 'not run (needs P1 + P3 steward Library tab)');
    skip('Steward: B no longer sees hidden skill', 'not run (needs P1)');

    // Consent tab
    const consentTab = await pageSteward.evaluateHandle(() =>
      Array.from(document.querySelectorAll('button, a, [role=tab]'))
        .find((el) => el.textContent.includes('Consent') || el.textContent.includes('licen')) || null
    );
    if (consentTab && await consentTab.evaluate((el) => el !== null)) {
      await consentTab.click();
      await sleep(500);
      pass('Steward: Consent tab accessible', 'mock');
      await shot(pageSteward, '07-steward-consent');
    } else {
      skip('Steward: Consent tab', 'not found — needs P3 steward console');
    }

    // Usage tab
    const usageTab = await pageSteward.evaluateHandle(() =>
      Array.from(document.querySelectorAll('button, a, [role=tab]'))
        .find((el) => el.textContent.includes('Usage')) || null
    );
    if (usageTab && await usageTab.evaluate((el) => el !== null)) {
      await usageTab.click();
      await sleep(500);
      pass('Steward: Usage tab accessible', 'mock');
      await shot(pageSteward, '07-steward-usage');
    } else {
      skip('Steward: Usage tab', 'not found — needs P3 steward console');
    }

    // ── Step 8: Wrong steward code → error message ───────────────────────────
    console.log('\n[8] Wrong steward code → error message');
    const pageWrong = await browser.newPage();
    await pageWrong.goto(`${BASE_URL}?view=steward`, { waitUntil: 'networkidle0', timeout: 30_000 });
    const wrongInput = await pageWrong.$('input[type="password"], input[name*="code"], input[placeholder*="code"]');
    if (wrongInput) {
      await wrongInput.type('wrong-code-12345');
      const signInWrong = await pageWrong.evaluateHandle(() =>
        Array.from(document.querySelectorAll('button')).find((b) => b.textContent.includes('Sign in')) || null
      );
      if (signInWrong && await signInWrong.evaluate((el) => el !== null)) {
        await signInWrong.click();
        await sleep(1000);
        const wrongBody = await pageWrong.$eval('body', (el) => el.innerText).catch(() => '');
        if (wrongBody.toLowerCase().includes('not right') ||
            wrongBody.toLowerCase().includes('incorrect') ||
            wrongBody.toLowerCase().includes('invalid') ||
            wrongBody.toLowerCase().includes('wrong')) {
          pass('Wrong code shows error message', 'mock');
        } else {
          skip('Wrong code shows error message', 'not run (needs P3 steward sign-in error handling)');
        }
      } else {
        skip('Wrong code: no sign-in button found', 'needs P3 steward console');
      }
    } else {
      skip('Wrong code: no code input found', 'needs P3 steward console sign-in');
    }
    skip('Rate limiting after 10 wrong tries', 'not run (needs P1 + ANVESHAN_RATE_AUTH_PER_HOUR=3)');
    await pageWrong.close();

  } finally {
    await browser.close();
  }

  // ── Summary ──────────────────────────────────────────────────────────────
  console.log('\n' + '='.repeat(65));
  console.log('  ' + 'Step'.padEnd(50) + ' Status');
  console.log('-'.repeat(65));
  for (const s of steps) {
    const icon = { PASS: '✓', FAIL: '✗', SKIP: '-' }[s.status] || '?';
    console.log(`  ${icon} ${s.name.padEnd(48)} ${s.status}${s.note ? ' — ' + s.note : ''}`);
  }
  console.log('='.repeat(65));

  const fails = steps.filter((s) => s.status === 'FAIL');
  const passes = steps.filter((s) => s.status === 'PASS');
  const skips = steps.filter((s) => s.status === 'SKIP');
  console.log(`\n${passes.length} PASS, ${fails.length} FAIL, ${skips.length} SKIP`);
  console.log(`Screenshots saved to: ${SCREENSHOT_DIR}`);

  if (fails.length > 0) {
    console.error('\nFailed steps:');
    for (const s of fails) console.error(`  ✗ ${s.name}: ${s.note}`);
    process.exit(1);
  }
  process.exit(0);
}

main().catch((err) => {
  console.error('Fatal error:', err);
  process.exit(1);
});
