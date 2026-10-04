import puppeteer from 'puppeteer-core';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const CHROME_PATH = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const URL = 'http://localhost:5173';

// Generate filesystem-safe ISO timestamp: YYYY-MM-DDTHH-mm-ssZ
const runTimestamp = new Date().toISOString().replace(/:/g, '-').replace(/\..+/, '') + 'Z';
// Always target root/screenshots directory
const BASE_SCREENSHOT_DIR = path.resolve(__dirname, '../../screenshots');
const RUN_DIR = path.join(BASE_SCREENSHOT_DIR, 'runs', runTimestamp);
const LATEST_DIR = path.join(BASE_SCREENSHOT_DIR, 'latest');

fs.mkdirSync(RUN_DIR, { recursive: true });
fs.mkdirSync(LATEST_DIR, { recursive: true });

async function saveScreenshot(page, baseName, options = {}) {
  const timestampedFileName = `${baseName}_${runTimestamp}.png`;
  const runPath = path.join(RUN_DIR, timestampedFileName);
  const latestPath = path.join(LATEST_DIR, `${baseName}.png`);

  await page.screenshot({ path: runPath, ...options });
  fs.copyFileSync(runPath, latestPath);
  console.log(`Screenshot saved:`);
  console.log(`  ├─ Timestamped: ${runPath}`);
  console.log(`  └─ Latest:      ${latestPath}`);
  return { runPath, latestPath, baseName, timestampedFileName };
}

async function runDevToolsAudit() {
  console.log('====================================================');
  console.log(`ANVESHAN // COMPREHENSIVE DEVTOOLS AUDIT [${runTimestamp}]`);
  console.log('====================================================');
  console.log(`Connecting Chrome executable: ${CHROME_PATH}`);

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

  // 1. Hook Chrome DevTools Console Listener
  page.on('console', (msg) => {
    const type = msg.type();
    const text = msg.text();
    consoleLogs.push({ type, text, location: msg.location() });

    if (type === 'error') {
      consoleErrors.push({ text, location: msg.location() });
      console.error(`[CDP CONSOLE ERROR] ${text}`);
    } else if (type === 'warning') {
      console.warn(`[CDP CONSOLE WARN] ${text}`);
    }
  });

  // 2. Hook Uncaught Page Exceptions
  page.on('pageerror', (err) => {
    pageErrors.push({ message: err.message, stack: err.stack });
    console.error(`[CDP UNCAUGHT EXCEPTION] ${err.message}`);
  });

  // 3. Hook Network Interceptor
  page.on('requestfailed', (req) => {
    const failure = req.failure();
    const url = req.url();
    failedRequests.push({ url, method: req.method(), errorText: failure ? failure.errorText : 'Unknown' });
    console.error(`[CDP NETWORK FAIL] ${req.method()} ${url} -> ${failure ? failure.errorText : 'FAILED'}`);
  });

  page.on('response', (res) => {
    const status = res.status();
    const url = res.url();
    loadedResources.push({ url, status, type: res.request().resourceType() });
    if (status >= 400) {
      console.error(`[CDP HTTP ${status}] ${url}`);
      failedRequests.push({ url, method: res.request().method(), status, errorText: `HTTP ${status}` });
    }
  });

  console.log(`Navigating to ${URL}...`);
  const navStart = performance.now();
  await page.goto(URL, { waitUntil: 'networkidle0', timeout: 30000 });
  const navDuration = Math.round(performance.now() - navStart);
  console.log(`Navigation complete in ${navDuration}ms.`);

  // 4. Verify Core DOM Elements
  console.log('\n--- VERIFYING CORE DOM ELEMENTS ---');
  const title = await page.title();
  console.log(`Page Title: "${title}"`);

  const headerBrand = await page.$eval('header', (el) => el.innerText);
  console.log(`Header Mounted: ${headerBrand.includes('ANVESHAN') ? 'PASS' : 'FAIL'}`);

  const decks = await page.$$eval('div', (els) =>
    els.filter((e) => e.innerText && e.innerText.includes('EXPERT REFERENCE') && e.innerText.includes('LEARNER ATTEMPT')).length
  );
  console.log(`Dual-Deck Player Mounted: ${decks > 0 ? 'PASS' : 'FAIL'}`);

  const images = await page.$$eval('img', (imgs) =>
    imgs.map((img) => ({ src: img.src, complete: img.complete, naturalWidth: img.naturalWidth }))
  );
  console.log(`Images Verified on Page (${images.length}): all loaded = ${images.every((i) => i.complete && i.naturalWidth > 0)}`);

  // 5. CAPTURING COMPREHENSIVE 15-SCREEN GALLERY
  console.log('\n--- CAPTURING COMPREHENSIVE SCREEN GALLERY ---');

  // Screen 1: Canonical Forensic Transmission Instrument (Micrometer)
  console.log('\n[Screen 1/15] Capturing Forensic Transmission Instrument Workbench...');
  const ss1 = await saveScreenshot(page, '01_workbench_micrometer', { fullPage: true });
  savedScreenshots.push(ss1);

  // Screen 2: Lineage Merkle Provenance DAG Drawer
  console.log('\n[Screen 2/15] Opening Cryptographic Lineage DAG Drawer...');
  await page.evaluate(() => {
    const btn = Array.from(document.querySelectorAll('button, a')).find((b) => b.innerText.includes('VIEW PROVENANCE DAG'));
    if (btn) btn.click();
  });
  await new Promise((r) => setTimeout(r, 600));
  const ss2 = await saveScreenshot(page, '02_lineage_dag');
  savedScreenshots.push(ss2);

  // Close Lineage Drawer
  await page.evaluate(() => {
    const xBtn = Array.from(document.querySelectorAll('button')).find((b) => b.querySelector('svg.lucide-x'));
    if (xBtn) xBtn.click();
  });
  await new Promise((r) => setTimeout(r, 400));

  // Screen 3: Discovery / Capability Portfolio Landing
  console.log('\n[Screen 3/15] Navigating to 00. PORTFOLIO (Discovery View)...');
  await page.evaluate(() => {
    const btn = Array.from(document.querySelectorAll('button')).find((b) => b.innerText.includes('00.') && b.innerText.includes('PORTFOLIO'));
    if (btn) btn.click();
  });
  await new Promise((r) => setTimeout(r, 600));
  const ss3 = await saveScreenshot(page, '03_portfolio_discovery', { fullPage: true });
  savedScreenshots.push(ss3);

  // Screen 4: Stage 01 Source & Grounding (Kolam Case)
  console.log('\n[Screen 4/15] Selecting Kolam and inspecting 01. SOURCE & Grounding...');
  await page.evaluate(() => {
    const sel = document.querySelector('select');
    if (sel) {
      sel.value = 'kolam';
      sel.dispatchEvent(new Event('change', { bubbles: true }));
    }
    const sourceBtn = Array.from(document.querySelectorAll('button')).find((b) => b.innerText.includes('01.') && b.innerText.includes('SOURCE'));
    if (sourceBtn) sourceBtn.click();
  });
  await new Promise((r) => setTimeout(r, 600));
  const ss4 = await saveScreenshot(page, '04_source_grounding_kolam', { fullPage: true });
  savedScreenshots.push(ss4);

  // Screen 5: Adaptive Spatial Practice Canvas (Kolam Case)
  console.log('\n[Screen 5/15] Composing Adaptive Spatial Practice Canvas for Kolam...');
  await page.evaluate(() => {
    const practiceBtn = Array.from(document.querySelectorAll('button')).find((b) => b.innerText.includes('COMPOSE ADAPTIVE WORKSPACE') || (b.innerText.includes('02.') && b.innerText.includes('PRACTICE')));
    if (practiceBtn) practiceBtn.click();
  });
  await new Promise((r) => setTimeout(r, 600));
  const ss5 = await saveScreenshot(page, '05_adaptive_workspace_kolam', { fullPage: true });
  savedScreenshots.push(ss5);

  // Screen 6: First Divergence Modal (Kolam Case)
  console.log('\n[Screen 6/15] Opening Forensic First Divergence Modal (Dot 3,4)...');
  await page.evaluate(() => {
    const btn = Array.from(document.querySelectorAll('button')).find((b) => b.innerText.includes('JUMP TO FIRST DIVERGENCE'));
    if (btn) btn.click();
  });
  await new Promise((r) => setTimeout(r, 600));
  const ss6 = await saveScreenshot(page, '06_first_divergence_modal');
  savedScreenshots.push(ss6);

  // Screen 7: Bounded Micro-Practice Retry Modal
  console.log('\n[Screen 7/15] Launching Bounded Micro-Practice Retry Modal...');
  await page.evaluate(() => {
    const btn = Array.from(document.querySelectorAll('button')).find((b) => b.innerText.includes('LAUNCH TARGETED RETRY'));
    if (btn) btn.click();
  });
  await new Promise((r) => setTimeout(r, 600));
  const ss7 = await saveScreenshot(page, '07_micropractice_modal');
  savedScreenshots.push(ss7);

  // Perform retry correction and advance
  console.log('Executing Micro-Practice Retry Action (Option B)...');
  await page.evaluate(() => {
    const optB = Array.from(document.querySelectorAll('button')).find((b) => b.innerText.includes('Continuous Orbital Convex Arc'));
    if (optB) optB.click();
  });
  await new Promise((r) => setTimeout(r, 400));

  await page.evaluate(() => {
    const submitBtn = Array.from(document.querySelectorAll('button')).find((b) => b.innerText.includes('SUBMIT VERIFIED RETRY'));
    if (submitBtn) submitBtn.click();
  });
  await new Promise((r) => setTimeout(r, 600));

  // Screen 8: Transmission Complete View (Kolam Case)
  console.log('\n[Screen 8/15] Capturing Transmission Complete View (+4.3 PTS GAIN)...');
  const ss8 = await saveScreenshot(page, '08_transmission_complete_kolam', { fullPage: true });
  savedScreenshots.push(ss8);

  // Screen 9: Diagnostic Workspace (Bicycle Repair Case)
  console.log('\n[Screen 9/15] Switching to Bicycle Repair -> Diagnostic Workspace...');
  await page.evaluate(() => {
    const sel = document.querySelector('select');
    if (sel) {
      sel.value = 'bicycle_repair';
      sel.dispatchEvent(new Event('change', { bubbles: true }));
    }
    const practiceBtn = Array.from(document.querySelectorAll('button')).find((b) => b.innerText.includes('02.') && b.innerText.includes('PRACTICE'));
    if (practiceBtn) practiceBtn.click();
  });
  await new Promise((r) => setTimeout(r, 600));
  const ss9 = await saveScreenshot(page, '09_diagnostic_workspace_bike', { fullPage: true });
  savedScreenshots.push(ss9);

  // Screen 10: Rhythm Practice Instrument (Tabla Case)
  console.log('\n[Screen 10/15] Switching to Tabla -> Rhythm Practice Instrument...');
  await page.evaluate(() => {
    const sel = document.querySelector('select');
    if (sel) {
      sel.value = 'tabla';
      sel.dispatchEvent(new Event('change', { bubbles: true }));
    }
  });
  await new Promise((r) => setTimeout(r, 600));
  const ss10 = await saveScreenshot(page, '10_rhythm_workspace_tabla', { fullPage: true });
  savedScreenshots.push(ss10);

  // Screen 11: State Transition Workspace (Handloom Weaving Case)
  console.log('\n[Screen 11/15] Switching to Handloom Weaving -> State Transition Workspace...');
  await page.evaluate(() => {
    const sel = document.querySelector('select');
    if (sel) {
      sel.value = 'weaving';
      sel.dispatchEvent(new Event('change', { bubbles: true }));
    }
  });
  await new Promise((r) => setTimeout(r, 600));
  const ss11 = await saveScreenshot(page, '11_state_transition_weaving', { fullPage: true });
  savedScreenshots.push(ss11);

  // Screen 12: Spatial Sequence Workspace (Origami Case)
  console.log('\n[Screen 12/15] Switching to Origami -> Spatial Sequence Workspace...');
  await page.evaluate(() => {
    const sel = document.querySelector('select');
    if (sel) {
      sel.value = 'origami';
      sel.dispatchEvent(new Event('change', { bubbles: true }));
    }
  });
  await new Promise((r) => setTimeout(r, 600));
  const ss12 = await saveScreenshot(page, '12_spatial_sequence_origami', { fullPage: true });
  savedScreenshots.push(ss12);

  // Screen 13: First-Divergence Workspace (Square Knot Case)
  console.log('\n[Screen 13/15] Switching to Square Knot -> First-Divergence Workspace...');
  await page.evaluate(() => {
    const sel = document.querySelector('select');
    if (sel) {
      sel.value = 'square_knot';
      sel.dispatchEvent(new Event('change', { bubbles: true }));
    }
  });
  await new Promise((r) => setTimeout(r, 600));
  const ss13 = await saveScreenshot(page, '13_first_divergence_knot', { fullPage: true });
  savedScreenshots.push(ss13);

  // Screen 14: Google Stitch Generative Canvas Modal
  console.log('\n[Screen 14/15] Opening Google Stitch Canvas Modal...');
  await page.evaluate(() => {
    const stitchBtn = Array.from(document.querySelectorAll('button')).find((b) => b.innerText.includes('STITCH CANVAS'));
    if (stitchBtn) stitchBtn.click();
  });
  await new Promise((r) => setTimeout(r, 600));
  const ss14 = await saveScreenshot(page, '14_stitch_canvas_modal');
  savedScreenshots.push(ss14);

  // Close Stitch Modal
  await page.evaluate(() => {
    const xBtn = Array.from(document.querySelectorAll('button')).find((b) => b.querySelector('svg.lucide-x'));
    if (xBtn) xBtn.click();
  });
  await new Promise((r) => setTimeout(r, 400));

  // Screen 15: Gemini Model Gateway Settings Modal
  console.log('\n[Screen 15/15] Opening Gemini Gateway Settings Modal...');
  await page.evaluate(() => {
    const settingsBtn = Array.from(document.querySelectorAll('header button')).find((b) => b.querySelector('svg.lucide-settings'));
    if (settingsBtn) settingsBtn.click();
  });
  await new Promise((r) => setTimeout(r, 600));
  const ss15 = await saveScreenshot(page, '15_gemini_settings_modal');
  savedScreenshots.push(ss15);

  // Close Settings Modal
  await page.evaluate(() => {
    const cancelBtn = Array.from(document.querySelectorAll('button')).find((b) => b.innerText.includes('CANCEL'));
    if (cancelBtn) cancelBtn.click();
  });
  await new Promise((r) => setTimeout(r, 400));

  // 6. Write Audit Manifest & Summary
  const allPassed = consoleErrors.length === 0 && pageErrors.length === 0 && failedRequests.length === 0;

  const auditReport = {
    run_timestamp: runTimestamp,
    execution_time_iso: new Date().toISOString(),
    navigation_duration_ms: navDuration,
    resources_loaded_count: loadedResources.length,
    console_messages_count: consoleLogs.length,
    console_errors_count: consoleErrors.length,
    uncaught_exceptions_count: pageErrors.length,
    failed_requests_count: failedRequests.length,
    audit_passed: allPassed,
    screenshots: savedScreenshots.map((s) => ({
      name: s.baseName,
      timestamped_file: s.timestampedFileName,
      relative_path: `runs/${runTimestamp}/${s.timestampedFileName}`,
    })),
  };

  const reportPath = path.join(RUN_DIR, 'audit_report.json');
  fs.writeFileSync(reportPath, JSON.stringify(auditReport, null, 2));

  // Update master manifest
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
    screenshots_count: savedScreenshots.length,
  });
  fs.writeFileSync(masterManifestPath, JSON.stringify(masterManifest, null, 2));

  console.log('\n====================================================');
  console.log('CHROME DEVTOOLS AUDIT SUMMARY:');
  console.log('====================================================');
  console.log(`Run Timestamp:            ${runTimestamp}`);
  console.log(`Total Resources Loaded:   ${loadedResources.length}`);
  console.log(`Total Console Messages:   ${consoleLogs.length}`);
  console.log(`Console Errors:           ${consoleErrors.length}`);
  console.log(`Uncaught Page Errors:     ${pageErrors.length}`);
  console.log(`Failed Network Requests:  ${failedRequests.length}`);
  console.log(`Screenshots Captured:     ${savedScreenshots.length}`);
  console.log(`Run Directory:            ${RUN_DIR}`);
  console.log(`Latest Pointer Directory: ${LATEST_DIR}`);
  console.log(`Audit Report:             ${reportPath}`);
  console.log(`Master Manifest:          ${masterManifestPath}`);

  console.log(`\nALL IN TACT AUDIT RESULT: ${allPassed ? '>>> 100% HEALTHY & INTACT <<<' : 'ISSUES DETECTED'}`);

  await browser.close();
  return allPassed;
}

runDevToolsAudit()
  .then((passed) => {
    process.exit(passed ? 0 : 1);
  })
  .catch((err) => {
    console.error('Fatal audit failure:', err);
    process.exit(1);
  });
