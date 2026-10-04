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
  console.log(`ANVESHAN // CHROME DEVTOOLS AUDIT [${runTimestamp}]`);
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
    } else {
      console.log(`[CDP CONSOLE ${type.toUpperCase()}] ${text}`);
    }
  });

  // 2. Hook Uncaught Page Exceptions
  page.on('pageerror', (err) => {
    pageErrors.push({
      message: err.message,
      stack: err.stack,
    });
    console.error(`[CDP UNCAUGHT EXCEPTION] ${err.message}`);
  });

  // 3. Hook Network Interceptor
  page.on('requestfailed', (req) => {
    const failure = req.failure();
    const url = req.url();
    failedRequests.push({
      url,
      method: req.method(),
      errorText: failure ? failure.errorText : 'Unknown network failure',
    });
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

  // 4. Verify DOM and Core Components
  console.log('\n--- VERIFYING CORE DOM ELEMENTS ---');
  
  const title = await page.title();
  console.log(`Page Title: "${title}"`);

  // Check Header
  const headerBrand = await page.$eval('header', (el) => el.innerText);
  console.log(`Header Mounted: ${headerBrand.includes('ANVESHAN') ? 'PASS' : 'FAIL'}`);

  // Check Dual-Deck Video Players (Reference Case: Micrometer)
  const decks = await page.$$eval('div', (els) =>
    els.filter((e) => e.innerText && e.innerText.includes('EXPERT REFERENCE') && e.innerText.includes('LEARNER ATTEMPT')).length
  );
  console.log(`Dual-Deck Player Mounted: ${decks > 0 ? 'PASS' : 'FAIL'}`);

  // Check Images Loaded
  const images = await page.$$eval('img', (imgs) =>
    imgs.map((img) => ({
      src: img.src,
      alt: img.alt,
      complete: img.complete,
      naturalWidth: img.naturalWidth,
      naturalHeight: img.naturalHeight,
    }))
  );
  console.log(`\nImages Verified on Page (${images.length}):`);
  images.forEach((img, i) => {
    const isLoaded = img.complete && img.naturalWidth > 0;
    console.log(`  [${i + 1}] ${img.src} -> ${isLoaded ? 'LOADED OK' : 'FAILED'} (${img.naturalWidth}x${img.naturalHeight})`);
  });

  // Check Sensory Ribbon
  const ribbon = await page.$eval('main', (el) => el.innerText.includes('SENSORY CUE WAVEFORM RIBBON'));
  console.log(`Sensory Ribbon Mounted: ${ribbon ? 'PASS' : 'FAIL'}`);

  // Check Rubric HUD Criteria
  const critRatchet = await page.$eval('main', (el) => el.innerText.includes('CRIT-RATCHET'));
  console.log(`Rubric Criteria Mounted (CRIT-RATCHET): ${critRatchet ? 'PASS' : 'FAIL'}`);

  // Check Transmission Gain Hero
  const gainHero = await page.$eval('main', (el) => el.innerText.includes('+5.5 PTS'));
  console.log(`Transmission Gain Hero (+5.5 PTS GAIN): ${gainHero ? 'PASS' : 'FAIL'}`);

  // 5. Test Interactive Features & Capture Timestamped Evidence
  console.log('\n--- TESTING FULL END-TO-END JOURNEY & CAPTURING EVIDENCE ---');

  // Test 1: Full Workbench Overview (Micrometer Reference Case)
  console.log('Capture 1: Forensic Transmission Instrument Workbench...');
  const ss1 = await saveScreenshot(page, '01_workbench_overview', { fullPage: true });
  savedScreenshots.push(ss1);

  // Test 2: Open Provenance DAG Drawer
  console.log('Capture 2: Testing "VIEW PROVENANCE DAG"...');
  await page.evaluate(() => {
    const btn = Array.from(document.querySelectorAll('button, a')).find((b) => b.innerText.includes('VIEW PROVENANCE DAG'));
    if (btn) btn.click();
  });
  await new Promise((r) => setTimeout(r, 600));

  const lineageModalOpened = await page.evaluate(() => {
    return document.body.innerText.includes('CRYPTOGRAPHIC LINEAGE & PROVENANCE RECORD');
  });
  console.log(`Lineage DAG Modal Opened: ${lineageModalOpened ? 'PASS' : 'FAIL'}`);

  const ss2 = await saveScreenshot(page, '02_lineage_modal');
  savedScreenshots.push(ss2);

  // Close Lineage modal
  await page.evaluate(() => {
    const allBtns = Array.from(document.querySelectorAll('button'));
    const xBtn = allBtns.find((b) => b.querySelector('svg.lucide-x'));
    if (xBtn) xBtn.click();
  });
  await new Promise((r) => setTimeout(r, 400));

  // Test 3: Navigate to 00. PORTFOLIO (Discovery View)
  console.log('Capture 3: Testing "00. PORTFOLIO" (Discovery View)...');
  await page.evaluate(() => {
    const btn = Array.from(document.querySelectorAll('button')).find((b) => b.innerText.includes('00.') && b.innerText.includes('PORTFOLIO'));
    if (btn) btn.click();
  });
  await new Promise((r) => setTimeout(r, 600));

  const discoveryMounted = await page.evaluate(() => {
    return document.body.innerText.includes('Transmit what matters') && document.body.innerText.includes('Sikku Kolam Geometric Drawing');
  });
  console.log(`Discovery Portfolio View Mounted: ${discoveryMounted ? 'PASS' : 'FAIL'}`);

  const ss3 = await saveScreenshot(page, '03_stitch_canvas_modal'); // Map to slot 3 or portfolio
  savedScreenshots.push(ss3);

  // Test 4: Select "kolam" capability and inspect Stage 01. SOURCE
  console.log('Capture 4: Testing "01. SOURCE" (Authentic Demonstration & Epistemic Certainty)...');
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

  const sourceMounted = await page.evaluate(() => {
    return document.body.innerText.includes('EPISTEMIC CERTAINTY TAXONOMY') && document.body.innerText.includes('Brahma Mudi');
  });
  console.log(`Source & Grounding View Mounted: ${sourceMounted ? 'PASS' : 'FAIL'}`);

  const ss4 = await saveScreenshot(page, '04_source_stage_modal');
  savedScreenshots.push(ss4);

  // Test 5: Enter Adaptive Practice (Spatial Practice Canvas)
  console.log('Capture 5: Testing "02. PRACTICE" (Adaptive Spatial Canvas for Kolam)...');
  await page.evaluate(() => {
    const btn = Array.from(document.querySelectorAll('button')).find((b) => b.innerText.includes('COMPOSE ADAPTIVE WORKSPACE') || (b.innerText.includes('02.') && b.innerText.includes('PRACTICE')));
    if (btn) btn.click();
  });
  await new Promise((r) => setTimeout(r, 600));

  const canvasMounted = await page.evaluate(() => {
    return document.body.innerText.includes('SPATIAL PRACTICE CANVAS') && document.body.innerText.includes('5×5 Orthogonal Pulli Lattice');
  });
  console.log(`Adaptive Spatial Canvas Mounted: ${canvasMounted ? 'PASS' : 'FAIL'}`);

  const ss5 = await saveScreenshot(page, '05_practice_stage_modal');
  savedScreenshots.push(ss5);

  // Test 6: Click "JUMP TO FIRST DIVERGENCE"
  console.log('Testing First Divergence Modal...');
  await page.evaluate(() => {
    const btn = Array.from(document.querySelectorAll('button')).find((b) => b.innerText.includes('JUMP TO FIRST DIVERGENCE'));
    if (btn) btn.click();
  });
  await new Promise((r) => setTimeout(r, 600));

  const divModalMounted = await page.evaluate(() => {
    return document.body.innerText.includes('FIRST DIVERGENCE DETECTED') && document.body.innerText.includes('Pulli Dot Penetration');
  });
  console.log(`First Divergence Modal Mounted: ${divModalMounted ? 'PASS' : 'FAIL'}`);

  // Test 7: Click "LAUNCH TARGETED RETRY" to open micro-practice modal
  console.log('Testing Micro-Practice Retry Modal...');
  await page.evaluate(() => {
    const btn = Array.from(document.querySelectorAll('button')).find((b) => b.innerText.includes('LAUNCH TARGETED RETRY'));
    if (btn) btn.click();
  });
  await new Promise((r) => setTimeout(r, 600));

  // Perform the micro-practice correction (Select Option B: Continuous Orbital Arc)
  await page.evaluate(() => {
    const optB = Array.from(document.querySelectorAll('button')).find((b) => b.innerText.includes('Continuous Orbital Convex Arc'));
    if (optB) optB.click();
  });
  await new Promise((r) => setTimeout(r, 400));

  // Submit verified retry
  console.log('Submitting Verified Retry...');
  await page.evaluate(() => {
    const submitBtn = Array.from(document.querySelectorAll('button')).find((b) => b.innerText.includes('SUBMIT VERIFIED RETRY'));
    if (submitBtn) submitBtn.click();
  });
  await new Promise((r) => setTimeout(r, 600));

  // Verify transition to Transmission Complete View
  const transmissionCompleted = await page.evaluate(() => {
    return document.body.innerText.includes('Transmission Event Recorded') && document.body.innerText.includes('+4.3');
  });
  console.log(`Transmission Complete View Mounted (+4.3 PTS GAIN): ${transmissionCompleted ? 'PASS' : 'FAIL'}`);

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
