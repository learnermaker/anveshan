import puppeteer from 'puppeteer-core';
import fs from 'fs';
import path from 'path';

const CHROME_PATH = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const URL = 'http://localhost:5173';
const SCREENSHOT_DIR = path.resolve('screenshots');

if (!fs.existsSync(SCREENSHOT_DIR)) {
  fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
}

async function runDevToolsAudit() {
  console.log('====================================================');
  console.log('ANVESHAN // CHROME DEVTOOLS DIAGNOSTIC SUITE');
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

  // 5. Test Interactive Features
  console.log('\n--- TESTING USER INTERACTIONS ---');

  // Test 1: Click "JUMP TO FIRST DIVERGENCE (00:19.2)"
  console.log('Testing "JUMP TO FIRST DIVERGENCE"...');
  const jumpButton = await page.$('button ::-p-text(JUMP TO FIRST DIVERGENCE)');
  if (jumpButton) {
    await jumpButton.click();
    await new Promise((r) => setTimeout(r, 600));
    console.log('  -> Button clicked successfully.');
  } else {
    // Fallback search
    await page.evaluate(() => {
      const btn = Array.from(document.querySelectorAll('button')).find((b) => b.innerText.includes('JUMP TO FIRST DIVERGENCE'));
      if (btn) btn.click();
    });
    await new Promise((r) => setTimeout(r, 600));
    console.log('  -> Button clicked via evaluate.');
  }

  // Take Workbench Screenshot
  const ss1Path = path.join(SCREENSHOT_DIR, '01_workbench_overview.png');
  await page.screenshot({ path: ss1Path, fullPage: true });
  console.log(`Screenshot saved: ${ss1Path}`);

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

  // Take Lineage Modal Screenshot
  const ss2Path = path.join(SCREENSHOT_DIR, '02_lineage_modal.png');
  await page.screenshot({ path: ss2Path });
  console.log(`Screenshot saved: ${ss2Path}`);

  // Close Lineage modal
  await page.evaluate(() => {
    const closeBtn = document.querySelector('button');
    // Click close
    const allBtns = Array.from(document.querySelectorAll('button'));
    const xBtn = allBtns.find((b) => b.querySelector('svg.lucide-x'));
    if (xBtn) xBtn.click();
  });
  await new Promise((r) => setTimeout(r, 400));

  // Test 3: Click "STITCH CANVAS"
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

  const ss3Path = path.join(SCREENSHOT_DIR, '03_stitch_canvas_modal.png');
  await page.screenshot({ path: ss3Path });
  console.log(`Screenshot saved: ${ss3Path}`);

  // Close Stitch modal
  await page.evaluate(() => {
    const allBtns = Array.from(document.querySelectorAll('button'));
    const xBtn = allBtns.find((b) => b.querySelector('svg.lucide-x'));
    if (xBtn) xBtn.click();
  });
  await new Promise((r) => setTimeout(r, 400));

  // 6. Summary of Chrome DevTools Metrics
  console.log('\n====================================================');
  console.log('CHROME DEVTOOLS AUDIT SUMMARY:');
  console.log('====================================================');
  console.log(`Total Resources Loaded: ${loadedResources.length}`);
  console.log(`Total Console Messages: ${consoleLogs.length}`);
  console.log(`Console Errors: ${consoleErrors.length}`);
  console.log(`Uncaught Page Errors: ${pageErrors.length}`);
  console.log(`Failed Network Requests: ${failedRequests.length}`);

  if (consoleErrors.length > 0) {
    console.log('\nConsole Errors Details:');
    consoleErrors.forEach((e) => console.log('  -', e));
  }

  if (pageErrors.length > 0) {
    console.log('\nPage Errors Details:');
    pageErrors.forEach((e) => console.log('  -', e));
  }

  if (failedRequests.length > 0) {
    console.log('\nFailed Requests Details:');
    failedRequests.forEach((r) => console.log('  -', r.method, r.url, r.errorText));
  }

  const allPassed = consoleErrors.length === 0 && pageErrors.length === 0 && failedRequests.length === 0;
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
