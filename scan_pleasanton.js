/**
 * Deep scan of pleasantoncustomhome — captures ALL image hashes including
 * those only visible through lightbox navigation.
 */
const { chromium } = require('/home/claudeuser/.npm/_npx/e41f203b7505f1fb/node_modules/playwright');
const fs = require('fs');

const LOGO = 'ff5b18_39307a9fb5f448aa8699880d142bb1fe';
const OPT  = '/home/claudeuser/agent/preview/assets/images-opt';

const onDisk = new Set(
  fs.readdirSync(OPT)
    .filter(f => f.startsWith('ff5b18_') && f.endsWith('.webp') && !f.includes('_ai_') && !/_\d+w\.webp$/.test(f))
    .map(f => f.replace('.webp', ''))
);

function extractHash(url) {
  if (!url) return null;
  const m = url.match(/ff5b18_([0-9a-f]{30,})/i);
  return m ? 'ff5b18_' + m[1] : null;
}

(async () => {
  const browser = await chromium.launch({ headless: true, args: ['--no-sandbox'] });
  const page = await browser.newPage();
  await page.setViewportSize({ width: 1440, height: 900 });

  // Intercept ALL network responses and capture any ff5b18 hash
  const networkHashes = new Set();
  page.on('response', async (resp) => {
    const url = resp.url();
    // Capture direct image loads from wixstatic
    if (url.includes('wixstatic.com/media/ff5b18_')) {
      const h = extractHash(url);
      if (h && !h.includes(LOGO)) networkHashes.add(h);
    }
    // Capture JSON/JS responses containing hashes
    const ct = resp.headers()['content-type'] || '';
    if (ct.includes('json') || ct.includes('javascript') || ct.includes('text')) {
      try {
        const text = await resp.text();
        if (!text.includes('ff5b18_')) return;
        const re = /ff5b18_([0-9a-f]{30,})/gi;
        let m;
        while ((m = re.exec(text)) !== null) {
          const h = 'ff5b18_' + m[1];
          if (!h.includes(LOGO)) networkHashes.add(h);
        }
      } catch(e) {}
    }
  });

  console.log('Loading pleasantoncustomhome...');
  await page.goto('https://www.ridgecrestdesigns.com/pleasantoncustomhome', { waitUntil: 'networkidle', timeout: 90000 });
  await page.waitForTimeout(4000);

  // Full scroll to load all lazy images
  let prevHeight = 0;
  for (let attempt = 0; attempt < 6; attempt++) {
    const height = await page.evaluate(() => document.body.scrollHeight);
    for (let y = prevHeight; y <= height; y += 300) {
      await page.evaluate((yy) => window.scrollTo(0, yy), y);
      await page.waitForTimeout(150);
    }
    prevHeight = height;
    await page.waitForTimeout(2000);
    const newHeight = await page.evaluate(() => document.body.scrollHeight);
    if (newHeight === height) break;
  }
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForTimeout(2000);

  console.log('Network hashes after scroll: ' + networkHashes.size);

  // Find all clickable gallery images
  const galleryImgs = await page.$$('img');
  const clickableWixImgs = [];
  for (const img of galleryImgs) {
    const src = await img.getAttribute('src') || '';
    if (src.includes('wixstatic.com/media/ff5b18_') && !src.includes(LOGO)) {
      clickableWixImgs.push({ el: img, src });
    }
  }
  console.log('Clickable wix images found in DOM: ' + clickableWixImgs.length);

  // Click the first one to open lightbox
  let lightboxOpened = false;
  for (const { el } of clickableWixImgs) {
    try {
      await el.scrollIntoViewIfNeeded();
      await page.waitForTimeout(300);
      await el.click({ timeout: 5000 });
      await page.waitForTimeout(2500);

      // Check if lightbox opened — look for any large image that appeared
      const bigImg = await page.evaluate(() => {
        const imgs = Array.from(document.querySelectorAll('img'));
        return imgs.some(img => {
          const r = img.getBoundingClientRect();
          return r.width > 400 && r.height > 300 && (img.src || '').includes('wixstatic');
        });
      });

      if (bigImg) {
        lightboxOpened = true;
        console.log('Lightbox opened!');
        break;
      }
    } catch(e) {}
  }

  if (lightboxOpened) {
    // Capture current lightbox image
    const captureLbHashes = async () => {
      return await page.evaluate((logo) => {
        const imgs = Array.from(document.querySelectorAll('img'));
        return imgs
          .filter(img => {
            const r = img.getBoundingClientRect();
            const src = img.src || '';
            return r.width > 300 && src.includes('wixstatic.com/media/ff5b18_') && !src.includes(logo);
          })
          .map(img => {
            const m = img.src.match(/ff5b18_([0-9a-f]{30,})/i);
            return m ? 'ff5b18_' + m[1] : null;
          })
          .filter(Boolean);
      }, LOGO);
    };

    const lbHashes = new Set();
    const firstHashes = await captureLbHashes();
    firstHashes.forEach(h => lbHashes.add(h));
    const firstHash = firstHashes[0];
    console.log('First lightbox image: ' + firstHash);

    // Navigate through entire lightbox
    let iterations = 0;
    const MAX = 300;

    while (iterations < MAX) {
      // Try various next button selectors
      const clicked = await page.evaluate(() => {
        // Look for next button by common patterns
        const selectors = [
          '[data-hook="next-item"]',
          '[aria-label="Next Item"]',
          '[aria-label="Next"]',
          'button[title="Next"]',
          '[data-testid="next-button"]',
        ];
        for (const sel of selectors) {
          const btn = document.querySelector(sel);
          if (btn) { btn.click(); return sel; }
        }
        // Try finding by position — rightmost button in any overlay
        const buttons = Array.from(document.querySelectorAll('button, [role="button"]'));
        const rightBtn = buttons.find(b => {
          const r = b.getBoundingClientRect();
          return r.left > window.innerWidth * 0.7 && r.top > 100 && r.top < window.innerHeight - 100 && r.width < 200;
        });
        if (rightBtn) { rightBtn.click(); return 'position-right'; }
        return null;
      });

      if (!clicked) {
        // Try keyboard navigation
        await page.keyboard.press('ArrowRight');
      }
      await page.waitForTimeout(700);

      const curHashes = await captureLbHashes();
      curHashes.forEach(h => lbHashes.add(h));

      // Loop detection
      if (iterations > 5 && firstHash && curHashes.includes(firstHash)) {
        console.log('Loop detected at iteration ' + iterations);
        break;
      }
      iterations++;
    }

    console.log('Lightbox navigation complete. Unique images found: ' + lbHashes.size);
    lbHashes.forEach(h => networkHashes.add(h));

    await page.keyboard.press('Escape');
    await page.waitForTimeout(500);
  } else {
    console.log('Lightbox did not open — relying on network interception only');
  }

  // Final wait for any pending network requests
  await page.waitForTimeout(3000);

  // Filter networkHashes to only real image hashes (exclude pageJsonFileName hashes)
  // Real gallery hashes end in _mv2, pageJsonFileName hashes end in _244
  const realHashes = new Set([...networkHashes].filter(h => {
    // pageJsonFileName hashes appear in context like _244, not as media URLs
    // We'll keep all hashes found via wixstatic.com/media/ URL
    return true; // keep all for now, we'll compare
  }));

  const missing = [...realHashes].filter(h => !onDisk.has(h));
  const have = [...realHashes].filter(h => onDisk.has(h));

  console.log('\n=== PLEASANTON CUSTOM RESULTS ===');
  console.log('Total unique ff5b18 hashes found: ' + realHashes.size);
  console.log('Already on our server: ' + have.length);
  console.log('NOT on our server: ' + missing.length);

  if (missing.length > 0) {
    console.log('\nMissing hashes:');
    missing.forEach(h => console.log('  ' + h));

    // Save for download
    fs.writeFileSync('/home/claudeuser/agent/pleasanton_missing.json',
      JSON.stringify(missing.map(h => ({ slug: 'pleasanton-custom', hash: h, ext: 'jpg' })), null, 2));
    console.log('\nSaved to pleasanton_missing.json');
  }

  await browser.close();
})().catch(e => { console.error('Fatal:', e.message); process.exit(1); });
