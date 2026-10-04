import puppeteer from 'puppeteer-core';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const CHROME_PATH =
  process.env.CHROME_PATH ||
  (process.platform === 'win32'
    ? 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
    : '/usr/bin/google-chrome');
const URL = process.env.ANVESHAN_URL || 'http://localhost:5173';

const runTimestamp = new Date().toISOString().replace(/:/g, '-').replace(/\..+/, '') + 'Z';
const BASE_SCREENSHOT_DIR = path.resolve(__dirname, '../../screenshots');
const RUN_DIR = path.join(BASE_SCREENSHOT_DIR, 'runs', runTimestamp);
const LATEST_DIR = path.join(BASE_SCREENSHOT_DIR, 'latest');
fs.mkdirSync(RUN_DIR, { recursive: true });
fs.mkdirSync(LATEST_DIR, { recursive: true });

const assertions = [];

function assertState(condition, message) {
  assertions.push({ message, passed: Boolean(condition) });
  if (!condition) throw new Error(message);
}

async function clickByText(page, text, label = text) {
  const clicked = await page.evaluate((needle) => {
    const button = Array.from(document.querySelectorAll('button, a')).find((el) =>
      el.innerText.includes(needle)
    );
    if (!button) return false;
    button.click();
    return true;
  }, text);
  assertState(clicked, `Missing actionable control: ${label}`);
}

async function assertBodyContains(page, text, label = text) {
  const body = await page.$eval('body', (el) => el.innerText);
  assertState(body.includes(text), `Expected UI state "${label}" containing "${text}"`);
}

async function selectCaseAndAssert(page, caseId, workspaceTitle) {
  const selected = await page.$eval(
    'select',
    (el, value) => {
      const select = el;
      select.value = value;
      select.dispatchEvent(new Event('change', { bubbles: true }));
      return select.value;
    },
    caseId
  );
  assertState(selected === caseId, `Case selector rejected canonical case ID "${caseId}"`);
  await page.waitForTimeout(500);

  const actualSelected = await page.$eval('select', (el) => el.value);
  assertState(
    actualSelected === caseId,
    `Case transition failed: expected "${caseId}", got "${actualSelected}"`
  );
  // Workspace identity is asserted at the point the workspace is expected to be rendered.
}

async function saveScreenshot(page, baseName, options = {}) {
  const timestampedFileName = `${baseName}_${runTimestamp}.png`;
  const runPath = path.join(RUN_DIR, timestampedFileName);
  const latestPath = path.join(LATEST_DIR, `${baseName}.png`);
  await page.screenshot({ path: runPath, ...options });
  fs.copyFileSync(runPath, latestPath);
  return { runPath, latestPath, baseName, timestampedFileName };
}

async function runDevToolsAudit() {
  console.log(`ANVESHAN // STATEFUL DEVTOOLS AUDIT [${runTimestamp}]`);
  const browser = await puppeteer.launch({
    executablePath: CHROME_PATH,
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--window-size=1920,1080'],
    defaultViewport: { width: 1920, height: 1080 },
  });
  const page = await browser.newPage();
  const consoleLogs = [];
  const consoleErrors = [];
  const pageErrors = [];
  const failedRequests = [];
  const loadedResources = [];
  const savedScreenshots = [];

  page.on('console', (msg) => {
    const entry = { type: msg.type(), text: msg.text(), location: msg.location() };
    consoleLogs.push(entry);
    if (msg.type() === 'error') consoleErrors.push(entry);
  });
  page.on('pageerror', (err) => pageErrors.push({ message: err.message, stack: err.stack }));
  page.on('requestfailed', (req) => {
    const failure = req.failure();
    failedRequests.push({
      url: req.url(),
      method: req.method(),
      errorText: failure?.errorText || 'FAILED',
    });
  });
  page.on('response', (res) => {
    loadedResources.push({ url: res.url(), status: res.status(), type: res.request().resourceType() });
    if (res.status() >= 400) {
      failedRequests.push({
        url: res.url(),
        method: res.request().method(),
        status: res.status(),
        errorText: `HTTP ${res.status()}`,
      });
    }
  });

  await page.goto(URL, { waitUntil: 'networkidle0', timeout: 30000 });
  await assertBodyContains(page, 'ANVESHAN', 'application shell');

  savedScreenshots.push(await saveScreenshot(page, '01_landing_discovery', { fullPage: true }));

  // Kolam: lifecycle path and modal state assertions.
  await selectCaseAndAssert(page, 'kolam', 'Spatial Practice Canvas');
  await clickByText(page, '01.', 'SOURCE stage');
  await page.waitForTimeout(300);
  await assertBodyContains(page, 'SOURCE', 'Kolam source stage');
  savedScreenshots.push(await saveScreenshot(page, '02_source_grounding_kolam', { fullPage: true }));

  await clickByText(page, 'COMPOSE ADAPTIVE WORKSPACE', 'adaptive workspace');
  await page.waitForTimeout(300);
  await assertBodyContains(page, 'Spatial Practice Canvas', 'Kolam practice workspace');
  savedScreenshots.push(await saveScreenshot(page, '03_adaptive_workspace_kolam', { fullPage: true }));

  await clickByText(page, 'JUMP TO FIRST DIVERGENCE', 'first divergence');
  await page.waitForTimeout(300);
  await assertBodyContains(page, 'FIRST DIVERGENCE', 'first-divergence modal');
  savedScreenshots.push(await saveScreenshot(page, '04_first_divergence_modal'));

  await clickByText(page, 'LAUNCH TARGETED RETRY', 'targeted retry');
  await page.waitForTimeout(300);
  await assertBodyContains(page, 'MICRO-PRACTICE', 'micro-practice modal');
  savedScreenshots.push(await saveScreenshot(page, '05_micropractice_modal'));

  await clickByText(page, 'Continuous Orbital Convex Arc', 'retry correction');
  await page.waitForTimeout(200);
  await clickByText(page, 'SUBMIT VERIFIED RETRY', 'verified retry');
  await page.waitForTimeout(400);
  await assertBodyContains(page, 'TRANSMISSION', 'transmission result');
  savedScreenshots.push(await saveScreenshot(page, '06_transmission_complete_kolam', { fullPage: true }));

  await clickByText(page, 'PROVENANCE DAG', 'provenance DAG');
  await page.waitForTimeout(300);
  await assertBodyContains(page, 'PROVENANCE', 'lineage/provenance drawer');
  savedScreenshots.push(await saveScreenshot(page, '07_lineage_dag'));
  await page.evaluate(() => {
    const button = Array.from(document.querySelectorAll('button')).find((b) => b.querySelector('svg.lucide-x'));
    if (button) button.click();
  });
  await page.waitForTimeout(200);

  const cases = [
    ['micrometer', 'Forensic Transmission Instrument', '08_workbench_micrometer'],
    ['bicycle_repair', 'Diagnostic Workspace', '09_diagnostic_workspace_bike'],
    ['tabla', 'Rhythm Practice Instrument', '10_rhythm_workspace_tabla'],
    ['weaving', 'State Transition Workspace', '11_state_transition_weaving'],
    ['origami', 'Spatial Sequence Workspace', '12_spatial_sequence_origami'],
    ['square_knot', 'First-Divergence Workspace', '13_first_divergence_knot'],
  ];
  for (const [caseId, workspaceTitle, screenshotName] of cases) {
    await selectCaseAndAssert(page, caseId, workspaceTitle);
    await assertBodyContains(page, workspaceTitle, \`${caseId} -> ${workspaceTitle}\`);
    savedScreenshots.push(await saveScreenshot(page, screenshotName, { fullPage: true }));
  }

  await clickByText(page, 'STITCH CANVAS', 'Stitch canvas');
  await page.waitForTimeout(300);
  await assertBodyContains(page, 'STITCH', 'Stitch modal');
  savedScreenshots.push(await saveScreenshot(page, '14_stitch_canvas_modal'));
  await page.evaluate(() => {
    const button = Array.from(document.querySelectorAll('button')).find((b) => b.querySelector('svg.lucide-x'));
    if (button) button.click();
  });
  await page.waitForTimeout(200);

  const settingsButton = await page.$('header button');
  assertState(Boolean(settingsButton), 'Settings control is mounted');
  await page.evaluate(() => {
    const button = Array.from(document.querySelectorAll('header button')).find((b) =>
      b.querySelector('svg.lucide-settings')
    );
    if (button) button.click();
  });
  await page.waitForTimeout(300);
  await assertBodyContains(page, 'GEMINI', 'Gemini gateway settings modal');
  await assertBodyContains(page, 'REPLAY FIXTURE', 'replay/live execution mode');
  savedScreenshots.push(await saveScreenshot(page, '15_gemini_settings_modal'));
  await page.evaluate(() => {
    const button = Array.from(document.querySelectorAll('button')).find((b) => b.innerText.includes('CANCEL'));
    if (button) button.click();
  });

  const browserVersion = await browser.version();
  const allPassed =
    assertions.every((item) => item.passed) &&
    consoleErrors.length === 0 &&
    pageErrors.length === 0 &&
    failedRequests.length === 0;

  const auditReport = {
    run_timestamp: runTimestamp,
    execution_time_iso: new Date().toISOString(),
    url: URL,
    browser_version: browserVersion,
    resources_loaded_count: loadedResources.length,
    console_messages_count: consoleLogs.length,
    console_errors_count: consoleErrors.length,
    uncaught_exceptions_count: pageErrors.length,
    failed_requests_count: failedRequests.length,
    state_assertions_count: assertions.length,
    state_assertions_passed: assertions.filter((item) => item.passed).length,
    state_assertions_failed: assertions.filter((item) => !item.passed).length,
    audit_passed: allPassed,
    screenshots: savedScreenshots.map((s) => ({
      name: s.baseName,
      timestamped_file: s.timestampedFileName,
      relative_path: `runs/${runTimestamp}/${s.timestampedFileName}`,
    })),
  };

  const reportPath = path.join(RUN_DIR, 'audit_report.json');
  fs.writeFileSync(reportPath, JSON.stringify(auditReport, null, 2));

  const masterManifestPath = path.join(BASE_SCREENSHOT_DIR, 'manifest.json');
  let masterManifest = [];
  if (fs.existsSync(masterManifestPath)) {
    try {
      masterManifest = JSON.parse(fs.readFileSync(masterManifestPath, 'utf8'));
    } catch {
      masterManifest = [];
    }
  }
  masterManifest.unshift({
    run_timestamp: runTimestamp,
    report_file: `runs/${runTimestamp}/audit_report.json`,
    audit_passed: allPassed,
    state_assertions_passed: auditReport.state_assertions_passed,
    screenshots_count: savedScreenshots.length,
  });
  fs.writeFileSync(masterManifestPath, JSON.stringify(masterManifest, null, 2));

  console.log(JSON.stringify({
    audit_passed: allPassed,
    browser_version: browserVersion,
    console_errors: consoleErrors.length,
    page_errors: pageErrors.length,
    failed_requests: failedRequests.length,
    state_assertions: assertions.length,
    screenshots: savedScreenshots.length,
    report: reportPath,
  }, null, 2));

  await browser.close();
  return allPassed;
}

runDevToolsAudit()
  .then((passed) => process.exit(passed ? 0 : 1))
  .catch((err) => {
    console.error('Fatal audit failure:', err);
    process.exit(1);
  });
