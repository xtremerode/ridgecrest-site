/**
 * capture_and_save_images.js
 * Navigates the Wix pleasanton-custom page and captures actual image bytes
 * from network responses — no direct CDN download needed.
 * Saves images to /tmp/wix_captured/
 */
const { chromium } = require('/home/claudeuser/.npm/_npx/e41f203b7505f1fb/node_modules/playwright');
const fs = require('fs');
const path = require('path');

const OUT_DIR = '/tmp/wix_captured';
if (!fs.existsSync(OUT_DIR)) fs.mkdirSync(OUT_DIR, { recursive: true });

const LOGO = 'ff5b18_39307a9fb5f448aa8699880d142bb1fe';
const URL  = 'https://www.ridgecrestdesigns.com/pleasantoncustomhome';

// Target hashes we need — will save any we capture
const NEEDED = new Set([
  "ff5b18_fb13d3b2359f78413ad107f355e430f9","ff5b18_f5e2d1244a02ad4b45bfd23a704d13b1",
  "ff5b18_08d8dac4e3a27c47df39abce050ac573","ff5b18_bd1d0cb4625ee1b00b7b426e3e976cc7",
  "ff5b18_8885f7ff92419bcdbff73bf3f37891a7","ff5b18_58423d1c7470fe24b55a2930c1e06363",
  "ff5b18_5e781097d465071dffb668c0932bd04c","ff5b18_61ed1991484acd5e2d24ab8a17b41e38",
  "ff5b18_0b068dee485acd56a83b820cb6a5d347","ff5b18_693605de9e9e855daff2e291091436b9",
  "ff5b18_b69750b7a5656f396a626c37446ef852","ff5b18_5fff38fdf4152a62fd19e5a590fece6d",
  "ff5b18_772a97f4c6eee15290bbebce936d500a","ff5b18_f52258a7eee8ad639d64d1d791019e0e",
  "ff5b18_efc6822c7e7d2c009ad3e6a286b493f2","ff5b18_4938cae3572722d89b25bba372fd3117",
  "ff5b18_7e0b347d55f68742f4dff90c64ce2959","ff5b18_5e3c1469607d174bc87db6fa41ccc6ed",
  "ff5b18_39bf510f37eee923698067796469b9aa","ff5b18_ff33e00800168bfe4d94ca4a8ae15e88",
  "ff5b18_96c341602f7e57faad737ff0523f98be","ff5b18_6ec165395655f6597c08621eb9142702",
  "ff5b18_f18c74e8b9a782a3cd5453a12d2174f8","ff5b18_6f6932b21d975b0f87e3a6a6f78f055d",
  "ff5b18_5727bc1abe8e393f6be4db8be695bbdd","ff5b18_95dc5787f236acb1fdc762bc6963e53d",
  "ff5b18_d51f851b312a561107cdddda2b2d20f0","ff5b18_02cc34d6974b2f66e9e6c06d1bc66f4e",
  "ff5b18_d57ecd40640ccf15e5581e4b71e7b383","ff5b18_e7669e01d1a18a9e0b35b4c23a179412",
  "ff5b18_cedd6f07b9b796f7e2c0be46be5621f9","ff5b18_e038d4fe950b3e7968bb154c134d7521",
  "ff5b18_02ec1a01433cf7ae0b117c8ac649fb26","ff5b18_310b18bcf37b98d909bbb440258d60d1",
  "ff5b18_99e750b81be6a6c4565ce1bc2d89fcef","ff5b18_ec6f2d49d7083f3ed43f4fdd76904a8a",
  "ff5b18_f8e20fd87498b99d6769688c1c3422b0","ff5b18_a86b72f67a16a526b05787a493aa53b4",
  "ff5b18_e700a83513d9f58ed050c719702bc661","ff5b18_6ca95f02fa49ab6316e9560de4333aac",
  "ff5b18_3574a2d1d31f2c5396d9a95ce661c0cf","ff5b18_f99126ba9dd29ecfc95b3b52b3942885",
  "ff5b18_beb1c1e39c354dc958a6a5c25587e09f","ff5b18_3838ef51caaa71ec287d555db1e167b8",
  "ff5b18_389c2314b4e8678722c6d8eac8a62e0c","ff5b18_3c34d4072ce363457f88f86e2bee5338",
  "ff5b18_0d032d07e3c5dda7f1cdeb864c1ada6c","ff5b18_e421e99013aa794a231c8774881f9afb",
  "ff5b18_d3adf5e64eeadf0816739ca2c5f634f2","ff5b18_98f97a76f69c41dca1e0ddb7a927be32",
]);

function extractHash(url) {
  const m = url.match(/ff5b18_([0-9a-f]{32})/i);
  return m ? 'ff5b18_' + m[1] : null;
}

(async () => {
  const browser = await chromium.launch({ headless: true, args: ['--no-sandbox'] });
  const page = await browser.newPage();
  await page.setViewportSize({ width: 1440, height: 900 });

  const captured = {};

  // Intercept responses and save image bytes
  page.on('response', async (resp) => {
    const url = resp.url();
    if (!url.includes('wixstatic.com/media/ff5b18_')) return;
    const hash = extractHash(url);
    if (!hash || hash === LOGO || captured[hash]) return;
    if (!NEEDED.has(hash)) return;

    try {
      const ct = resp.headers()['content-type'] || '';
      if (!ct.includes('image') && !ct.includes('octet')) return;
      const body = await resp.body();
      if (body.length < 5000) return;

      // Determine extension
      let ext = 'jpg';
      if (ct.includes('png')) ext = 'png';
      else if (ct.includes('webp')) ext = 'webp';
      else if (url.includes('.png')) ext = 'png';
      else if (url.includes('.webp')) ext = 'webp';

      const outFile = path.join(OUT_DIR, `${hash}_mv2.${ext}`);
      fs.writeFileSync(outFile, body);
      captured[hash] = { file: outFile, ext, size: body.length };
      console.log(`  ✓ ${hash.slice(0,26)}... (${ext}, ${Math.round(body.length/1024)}KB)`);
    } catch(e) {}
  });

  console.log('Loading page...');
  await page.goto(URL, { waitUntil: 'networkidle', timeout: 90000 });
  await page.waitForTimeout(3000);

  // Scroll aggressively to trigger all lazy-loaded images
  console.log('Scrolling to load all images...');
  let prevH = 0;
  for (let i = 0; i < 12; i++) {
    const h = await page.evaluate(() => document.body.scrollHeight);
    for (let y = prevH; y <= h; y += 200) {
      await page.evaluate(yy => window.scrollTo(0, yy), y);
      await page.waitForTimeout(80);
    }
    prevH = h;
    await page.waitForTimeout(2000);
    const newH = await page.evaluate(() => document.body.scrollHeight);
    if (newH === h && i > 3) break;
  }

  // Click gallery images to trigger full-res loads
  console.log('Clicking gallery items for full-res...');
  const imgs = await page.$$('img[src*="wixstatic.com/media/ff5b18_"]');
  console.log(`  Found ${imgs.length} images to click`);
  for (let i = 0; i < Math.min(imgs.length, 80); i++) {
    try {
      await imgs[i].scrollIntoViewIfNeeded();
      await page.waitForTimeout(150);
      await imgs[i].click({ timeout: 2000 });
      await page.waitForTimeout(1000);
      await page.keyboard.press('Escape');
      await page.waitForTimeout(300);
    } catch(e) {}
  }

  await page.waitForTimeout(3000);
  await browser.close();

  const capturedCount = Object.keys(captured).length;
  const missed = [...NEEDED].filter(h => !captured[h]);

  console.log(`\nCaptured: ${capturedCount}/${NEEDED.size}`);
  if (missed.length) {
    console.log(`Still missing: ${missed.length}`);
    missed.forEach(h => console.log(`  ${h}`));
  }

  fs.writeFileSync('/tmp/wix_captured/results.json', JSON.stringify({ captured, missed }, null, 2));
})().catch(e => { console.error('Fatal:', e.message); process.exit(1); });
