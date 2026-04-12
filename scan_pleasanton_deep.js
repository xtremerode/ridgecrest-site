/**
 * scan_pleasanton_deep.js
 * Deep scan of pleasanton-custom Wix page.
 * Clicks gallery items, triggers lightbox, scrolls aggressively.
 * Outputs found hashes to stdout.
 */
const { chromium } = require('/home/claudeuser/.npm/_npx/e41f203b7505f1fb/node_modules/playwright');

const LOGO = 'ff5b18_39307a9fb5f448aa8699880d142bb1fe';
const URL = 'https://www.ridgecrestdesigns.com/pleasantoncustomhome';

function extractHash(url) {
  const m = url.match(/ff5b18_([0-9a-f]{32})/i);
  return m ? 'ff5b18_' + m[1] : null;
}

(async () => {
  const browser = await chromium.launch({ headless: true, args: ['--no-sandbox'] });
  const page = await browser.newPage();
  await page.setViewportSize({ width: 1440, height: 900 });

  const hashes = new Set();

  const handler = async (resp) => {
    const u = resp.url();
    if (u.includes('wixstatic.com/media/ff5b18_')) {
      const h = extractHash(u);
      if (h && h !== LOGO) hashes.add(h);
    }
    const ct = resp.headers()['content-type'] || '';
    if (ct.includes('json') || ct.includes('javascript') || ct.includes('text')) {
      try {
        const text = await resp.text();
        if (!text.includes('ff5b18_')) return;
        const re = /ff5b18_([0-9a-f]{32})/gi;
        let m;
        while ((m = re.exec(text)) !== null) {
          const h = 'ff5b18_' + m[1];
          if (h !== LOGO) hashes.add(h);
        }
      } catch(e) {}
    }
  };
  page.on('response', handler);

  console.log('Loading page...');
  await page.goto(URL, { waitUntil: 'networkidle', timeout: 90000 });
  await page.waitForTimeout(3000);

  // Aggressive scroll — 12 passes
  console.log('Scrolling...');
  let prevH = 0;
  for (let attempt = 0; attempt < 12; attempt++) {
    const h = await page.evaluate(() => document.body.scrollHeight);
    for (let y = prevH; y <= h; y += 200) {
      await page.evaluate(yy => window.scrollTo(0, yy), y);
      await page.waitForTimeout(60);
    }
    prevH = h;
    await page.waitForTimeout(2000);
    const newH = await page.evaluate(() => document.body.scrollHeight);
    if (newH === h && attempt > 3) break;
  }
  await page.waitForTimeout(2000);
  console.log(`After scroll: ${hashes.size} hashes`);

  // Try clicking gallery items to trigger lightbox / load full-res
  console.log('Clicking gallery items...');
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForTimeout(1000);

  // Find all clickable images in gallery
  const galleryImgs = await page.$$('img[src*="wixstatic.com/media/ff5b18_"]');
  console.log(`Found ${galleryImgs.length} gallery images to click`);

  for (let i = 0; i < Math.min(galleryImgs.length, 60); i++) {
    try {
      await galleryImgs[i].scrollIntoViewIfNeeded();
      await page.waitForTimeout(200);
      await galleryImgs[i].click({ timeout: 3000 });
      await page.waitForTimeout(1500);
      // Close any lightbox (press Escape)
      await page.keyboard.press('Escape');
      await page.waitForTimeout(500);
    } catch(e) {}
  }
  console.log(`After clicks: ${hashes.size} hashes`);

  // Also check page source for any embedded JSON
  const html = await page.content();
  const re = /ff5b18_([0-9a-f]{32})/gi;
  let m;
  while ((m = re.exec(html)) !== null) {
    const h = 'ff5b18_' + m[1];
    if (h !== LOGO) hashes.add(h);
  }

  await browser.close();

  // Filter: must match exact 32-char hex
  const filtered = [...hashes].filter(h => /^ff5b18_[0-9a-f]{32}$/.test(h));
  console.log(`\nTotal unique hashes: ${filtered.length}`);
  console.log(JSON.stringify(filtered, null, 2));
})().catch(e => { console.error('Fatal:', e.message); process.exit(1); });
