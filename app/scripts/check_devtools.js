import puppeteer from 'puppeteer-core';
import fs from 'fs';
import path from 'path';

const CHROME_PATH = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const URL = 'http://localhost:5173';

// Generate filesystem-safe ISO timestamp: YYYY-MM-DDTHH-mm-ssZ
const runTimestamp = new Date().toISOString().replace(/:/g, '-').replace(/\..+/, '') + 'Z';
const BASE_SCREENSHOT_DIR = path.resolve('screenshots');
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
    consoleLogs.push({ type, text });
    if (type === 'error') {
      consoleErrors.push(text);
      console.error(`[CDP Console Error] ${text}`);
    } else if (type === 'warning') {
      console.warn(`[CDP Console Warn] ${text}`);
    }
  });

  // 2. Hook Uncaught Page Exceptions
  page.on('pageerror', (err) => {
    pageErrors.push(err.message);
    console.error(`[CDP Uncaught Exception] ${err.message}`);
  });

  // 3. Hook Network Request / Failure Listeners
  page.on('requestfailed', (req) => {
    failedRequests.push({
      url: req.url(),
      method: req.method(),
      errorText: req.failure() ? req.failure().errorText : 'Unknown failure',
    });
    console.error(`[CDP Network Failed] ${req.method()} ${req.url()} - ${req.failure()?.errorText}`);
  });

  page.on('response', (res) => {
    loadedResources.push({
      url: res.url(),
      status: res.status(),
      contentType: res.headers()['content-type'] || '',
    });
  });

  console.log(`Navigating to ${URL}...`);
  const navStart = Date.now();
  await page.goto(URL, { waitUntil: 'networkidle0', timeout: 30000 });
  const navDuration = Date.now() - navStart;
  console.log(`Navigation complete in ${navDuration}ms.`);

  // 4. Verify DOM and Core Components
  console.log('\n--- VERIFYING CORE DOM ELEMENTS ---');
  
  const title = await page.title();
  console.log(`Page Title: "${title}"`);

  // Check Header
  const headerBrand = await page.$eval('header', (el) => el.innerText);
  console.log(`Header Mounted: ${headerBrand.includes('ANVESHAN') ? 'PASS' : 'FAIL'}`);

  // Check Dual-Deck Video Players
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
  const critWipe = await page.$eval('main', (el) => el.innerText.includes('CRIT-WIPE'));
  const critRatchet = await page.$eval('main', (el) => el.innerText.includes('CRIT-RATCHET'));
  const critLock = await page.$eval('main', (el) => el.innerText.includes('CRIT-LOCK'));
  console.log(`Rubric Criteria Mounted (CRIT-WIPE, CRIT-RATCHET, CRIT-LOCK): ${critWipe && critRatchet && critLock ? 'PASS' : 'FAIL'}`);

  // Check Transmission Gain Hero
  const gainHero = await page.$eval('main', (el) => el.innerText.includes('+5.5 PTS'));
  console.log(`Transmission Gain Hero (+5.5 PTS GAIN): ${gainHero ? 'PASS' : 'FAIL'}`);

  // 5. Test Interactive Features & Capture Timestamped Evidence
  console.log('\n--- TESTING USER INTERACTIONS & CAPTURING EVIDENCE ---');

  // Test 1: Click "JUMP TO FIRST DIVERGENCE (00:19.2)"
  console.log('Testing "JUMP TO FIRST DIVERGENCE"...');
  await page.evaluate(() => {
    const btn = Array.from(document.querySelectorAll('button')).find((b) => b.innerText.includes('JUMP TO FIRST DIVERGENCE'));
    if (btn) btn.click();
  });
  await new Promise((r) => setTimeout(r, 600));

  // Take Full Workbench Screenshot
  const ss1 = await saveScreenshot(page, '01_workbench_overview', { fullPage: true });
  savedScreenshots.push(ss1);

  // Test 2: Click "VIEW PROVENANCE DAG" to open Lineage Drawer
  console.log('Testing "VIEW PROVENANCE DAG"...');
  await page.evaluate(() => {
    const btn = Array.from(document.querySelectorAll('button, a')).find((b) => b.innerText.includes('VIEW PROVENANCE DAG') || b.innerText.includes('CRYPTOGRAPHIC LINEAGE'));
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

  // Test 3: Click "STITCH CANVAS" modal
  console.log('Testing "STITCH CANVAS" modal...');
  await page.evaluate(() => {
    const stitchBtn = Array.from(document.querySelectorAll('button')).find((b) => b.innerText.includes('STITCH CANVAS'));
    if (stitchBtn) stitchBtn.click();
  });
  await new Promise((r) => setTimeout(r, 600));

  const stitchModalOpened = await page.evaluate(() => {
    return document.body.innerText.includes('GOOGLE STITCH MCP');
  });
  console.log(`Stitch Canvas Modal Opened: ${stitchModalOpened ? 'PASS' : 'FAIL'}`);

  const ss3 = await saveScreenshot(page, '03_stitch_canvas_modal');
  savedScreenshots.push(ss3);

  // Close Stitch modal
  await page.evaluate(() => {
    const allBtns = Array.from(document.querySelectorAll('button'));
    const xBtn = allBtns.find((b) => b.querySelector('svg.lucide-x'));
    if (xBtn) xBtn.click();
  });
  await new Promise((r) => setTimeout(r, 400));

  // Test 4: Open Stage 01 (Source) in Lifecycle Stepper
  console.log('Testing Lifecycle Stepper: 01. SOURCE...');
  await page.evaluate(() => {
    const sourceBtn = Array.from(document.querySelectorAll('button')).find((b) => b.innerText.includes('01.') && b.innerText.includes('SOURCE'));
    if (sourceBtn) sourceBtn.click();
  });
  await new Promise((r) => setTimeout(r, 600));

  const sourceModalOpened = await page.evaluate(() => {
    return document.body.innerText.includes('STAGE 01: CAPTURE & CONSENT');
  });
  console.log(`Stage 01 Source Modal Opened: ${sourceModalOpened ? 'PASS' : 'FAIL'}`);

  const ss4 = await saveScreenshot(page, '04_source_stage_modal');
  savedScreenshots.push(ss4);

  // Close Source modal
  await page.evaluate(() => {
    const allBtns = Array.from(document.querySelectorAll('button'));
    const xBtn = allBtns.find((b) => b.querySelector('svg.lucide-x'));
    if (xBtn) xBtn.click();
  });
  await new Promise((r) => setTimeout(r, 400));

  // Test 5: Open Stage 03 (Practice) in Lifecycle Stepper
  console.log('Testing Lifecycle Stepper: 03. PRACTICE...');
  await page.evaluate(() => {
    const practiceBtn = Array.from(document.querySelectorAll('button')).find((b) => b.innerText.includes('03.') && b.innerText.includes('PRACTICE'));
    if (practiceBtn) practiceBtn.click();
  });
  await new Promise((r) => setTimeout(r, 600));

  const practiceModalOpened = await page.evaluate(() => {
    return document.body.innerText.includes('STAGE 03: PRACTICE TASK SPECIFICATION');
  });
  console.log(`Stage 03 Practice Modal Opened: ${practiceModalOpened ? 'PASS' : 'FAIL'}`);

  const ss5 = await saveScreenshot(page, '05_practice_stage_modal');
  savedScreenshots.push(ss5);

  // Close Practice modal
  await page.evaluate(() => {
    const allBtns = Array.from(document.querySelectorAll('button'));
    const xBtn = allBtns.find((b) => b.querySelector('svg.lucide-x'));
    if (xBtn) xBtn.click();
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

  // Update or append to master manifest
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
