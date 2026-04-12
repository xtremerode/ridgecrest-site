/**
 * Capture missing Pleasanton Custom + Cottage Kitchen images via browser interception.
 * Playwright visits the Wix gallery pages, scrolls through, navigates the lightbox,
 * and saves every image binary it intercepts from wixstatic.com to images-opt/.
 * Then uploads each captured image to the gallery API.
 */
const { chromium } = require('/home/claudeuser/.npm/_npx/e41f203b7505f1fb/node_modules/playwright');
const fs = require('fs');
const path = require('path');
const https = require('https');
const http = require('http');

const OPT_DIR = '/home/claudeuser/agent/preview/assets/images-opt';
const SERVER  = 'http://127.0.0.1:8081';
const TOKEN   = '35e8bdf6f9cddb3a140a3ac34a9dcb3963c7bff434ef8bd6fedfda70299b13f1';
const LOGO    = 'ff5b18_39307a9fb5f448aa8699880d142bb1fe';

// Missing hashes we specifically need (from gallery_json, not on disk)
const MISSING = {
  'pleasanton-custom': new Set([
    'ff5b18_fb13d3b2359f78413ad107f355e430f9',
    'ff5b18_f5e2d1244a02ad4b45bfd23a704d13b1',
    'ff5b18_08d8dac4e3a27c47df39abce050ac573',
    'ff5b18_bd1d0cb4625ee1b00b7b426e3e976cc7',
    'ff5b18_8885f7ff92419bcdbff73bf3f37891a7',
    'ff5b18_58423d1c7470fe24b55a2930c1e06363',
    'ff5b18_5e781097d465071dffb668c0932bd04c',
    'ff5b18_61ed1991484acd5e2d24ab8a17b41e38',
    'ff5b18_0b068dee485acd56a83b820cb6a5d347',
    'ff5b18_693605de9e9e855daff2e291091436b9',
    'ff5b18_b69750b7a5656f396a626c37446ef852',
    'ff5b18_5fff38fdf4152a62fd19e5a590fece6d',
    'ff5b18_772a97f4c6eee15290bbebce936d500a',
    'ff5b18_f52258a7eee8ad639d64d1d791019e0e',
    'ff5b18_efc6822c7e7d2c009ad3e6a286b493f2',
    'ff5b18_4938cae3572722d89b25bba372fd3117',
    'ff5b18_7e0b347d55f68742f4dff90c64ce2959',
    'ff5b18_5e3c1469607d174bc87db6fa41ccc6ed',
    'ff5b18_39bf510f37eee923698067796469b9aa',
    'ff5b18_ff33e00800168bfe4d94ca4a8ae15e88',
    'ff5b18_96c341602f7e57faad737ff0523f98be',
    'ff5b18_6ec165395655f6597c08621eb9142702',
    'ff5b18_f18c74e8b9a782a3cd5453a12d2174f8',
    'ff5b18_6f6932b21d975b0f87e3a6a6f78f055d',
    'ff5b18_5727bc1abe8e393f6be4db8be695bbdd',
    'ff5b18_95dc5787f236acb1fdc762bc6963e53d',
    'ff5b18_d51f851b312a561107cdddda2b2d20f0',
    'ff5b18_02cc34d6974b2f66e9e6c06d1bc66f4e',
    'ff5b18_d57ecd40640ccf15e5581e4b71e7b383',
    'ff5b18_e7669e01d1a18a9e0b35b4c23a179412',
    'ff5b18_cedd6f07b9b796f7e2c0be46be5621f9',
    'ff5b18_e038d4fe950b3e7968bb154c134d7521',
    'ff5b18_02ec1a01433cf7ae0b117c8ac649fb26',
    'ff5b18_310b18bcf37b98d909bbb440258d60d1',
    'ff5b18_99e750b81be6a6c4565ce1bc2d89fcef',
    'ff5b18_ec6f2d49d7083f3ed43f4fdd76904a8a',
    'ff5b18_f8e20fd87498b99d6769688c1c3422b0',
    'ff5b18_a86b72f67a16a526b05787a493aa53b4',
    'ff5b18_e700a83513d9f58ed050c719702bc661',
    'ff5b18_6ca95f02fa49ab6316e9560de4333aac',
    'ff5b18_3574a2d1d31f2c5396d9a95ce661c0cf',
    'ff5b18_f99126ba9dd29ecfc95b3b52b3942885',
    'ff5b18_beb1c1e39c354dc958a6a5c25587e09f',
    'ff5b18_3838ef51caaa71ec287d555db1e167b8',
    'ff5b18_389c2314b4e8678722c6d8eac8a62e0c',
    'ff5b18_3c34d4072ce363457f88f86e2bee5338',
    'ff5b18_0d032d07e3c5dda7f1cdeb864c1ada6c',
    'ff5b18_e421e99013aa794a231c8774881f9afb',
    'ff5b18_d3adf5e64eeadf0816739ca2c5f634f2',
    'ff5b18_98f97a76f69c41dca1e0ddb7a927be32',
  ]),
  'pleasanton-cottage-kitchen': new Set([
    'ff5b18_6a0e2b78d1e141b4a89e5e1234567890', // placeholder — will be discovered from page
  ])
};

// Get actual missing cottage kitchen hash from gallery_json
const { execSync } = require('child_process');
try {
  const result = execSync(
    `PGPASSWORD=StrongPass123! psql -h 127.0.0.1 -U agent_user -d marketing_agent -t -c ` +
    `"SELECT gallery_json FROM portfolio_projects WHERE slug='pleasanton-cottage-kitchen';"`,
    { encoding: 'utf8' }
  ).trim();
  const gallery = JSON.parse(result);
  MISSING['pleasanton-cottage-kitchen'].clear();
  for (const item of gallery) {
    const h = Array.isArray(item) ? item[0] : item;
    const base = h.replace(/_mv2$/, '');
    const diskPath = path.join(OPT_DIR, base + '_mv2.webp');
    const diskPath2 = path.join(OPT_DIR, base + '_mv2.jpg');
    const diskPath3 = path.join(OPT_DIR, h + '.webp');
    if (!fs.existsSync(diskPath) && !fs.existsSync(diskPath2) && !fs.existsSync(diskPath3)) {
      MISSING['pleasanton-cottage-kitchen'].add(base.endsWith('_mv2') ? base.replace(/_mv2$/, '') : base);
    }
  }
  console.log(`Cottage Kitchen missing hashes: ${MISSING['pleasanton-cottage-kitchen'].size}`);
} catch(e) {
  console.log('Could not query cottage kitchen gallery:', e.message);
}

function extractHash(url) {
  const m = url.match(/ff5b18_([0-9a-f]{30,})/i);
  return m ? 'ff5b18_' + m[1] : null;
}

function isWantedHash(hash, slug) {
  if (!hash || hash.includes(LOGO)) return false;
  const base = hash.replace(/_mv2$/, '');
  return MISSING[slug] && (MISSING[slug].has(base) || MISSING[slug].has(hash));
}

function uploadToGallery(slug, filePath, filename) {
  return new Promise((resolve, reject) => {
    const boundary = '----FormBoundary' + Math.random().toString(36).slice(2);
    const fileData = fs.readFileSync(filePath);
    const body = Buffer.concat([
      Buffer.from(`--${boundary}\r\nContent-Disposition: form-data; name="file"; filename="${filename}"\r\nContent-Type: image/jpeg\r\n\r\n`),
      fileData,
      Buffer.from(`\r\n--${boundary}--\r\n`)
    ]);
    const options = {
      hostname: '127.0.0.1',
      port: 8081,
      path: `/admin/api/gallery/${slug}/add-image`,
      method: 'POST',
      headers: {
        'X-Admin-Token': TOKEN,
        'Content-Type': `multipart/form-data; boundary=${boundary}`,
        'Content-Length': body.length
      }
    };
    const req = http.request(options, (res) => {
      let data = '';
      res.on('data', d => data += d);
      res.on('end', () => {
        try { resolve(JSON.parse(data)); } catch(e) { resolve({ raw: data }); }
      });
    });
    req.on('error', reject);
    req.write(body);
    req.end();
  });
}

async function processProject(browser, wixUrl, slug) {
  console.log(`\n${'='.repeat(60)}`);
  console.log(`Processing: ${slug} (${wixUrl})`);
  console.log(`Looking for ${MISSING[slug].size} missing images`);

  const captured = new Map(); // hash → Buffer
  const page = await browser.newPage();
  await page.setViewportSize({ width: 1440, height: 900 });

  // Intercept BINARY image responses
  page.on('response', async (resp) => {
    try {
      const url = resp.url();
      if (!url.includes('wixstatic.com/media/ff5b18_')) return;
      const hash = extractHash(url);
      if (!hash || !isWantedHash(hash, slug)) return;
      const ct = resp.headers()['content-type'] || '';
      if (!ct.includes('image') && !ct.includes('octet')) return;
      const body = await resp.body();
      if (body && body.length > 5000) {
        const base = hash.replace(/_mv2$/, '');
        if (!captured.has(base)) {
          captured.set(base, { data: body, url, ct });
          console.log(`  ✓ Captured ${base} (${(body.length/1024).toFixed(0)}KB) from browser`);
        }
      }
    } catch(e) {}
  });

  console.log('Loading page...');
  await page.goto(wixUrl, { waitUntil: 'networkidle', timeout: 60000 }).catch(() => {});
  await page.waitForTimeout(3000);

  // Scroll through entire page to trigger lazy loading
  console.log('Scrolling to trigger lazy loads...');
  let prevHeight = 0;
  for (let attempt = 0; attempt < 8; attempt++) {
    const height = await page.evaluate(() => document.body.scrollHeight);
    for (let y = prevHeight; y <= height; y += 200) {
      await page.evaluate((yy) => window.scrollTo(0, yy), y);
      await page.waitForTimeout(80);
    }
    prevHeight = height;
    await page.waitForTimeout(1500);
    const newHeight = await page.evaluate(() => document.body.scrollHeight);
    if (newHeight === height) break;
  }
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForTimeout(2000);
  console.log(`After scroll: captured ${captured.size}/${MISSING[slug].size}`);

  // Open lightbox and navigate through all images
  const galleryImgs = await page.$$('img');
  for (const img of galleryImgs) {
    try {
      const src = await img.getAttribute('src') || '';
      if (!src.includes('wixstatic.com/media/ff5b18_')) continue;
      await img.scrollIntoViewIfNeeded();
      await page.waitForTimeout(200);
      await img.click({ timeout: 3000 });
      await page.waitForTimeout(2000);

      // Detect lightbox
      const inLightbox = await page.evaluate(() =>
        Array.from(document.querySelectorAll('img')).some(i => {
          const r = i.getBoundingClientRect();
          return r.width > 500 && r.height > 300 && (i.src || '').includes('wixstatic');
        })
      );
      if (inLightbox) {
        console.log('Lightbox opened — navigating...');
        break;
      }
    } catch(e) {}
  }

  // Navigate lightbox if open
  const isLightboxOpen = await page.evaluate(() =>
    Array.from(document.querySelectorAll('img')).some(i => {
      const r = i.getBoundingClientRect();
      return r.width > 400 && r.height > 300 && (i.src || '').includes('wixstatic');
    })
  );

  if (isLightboxOpen) {
    let iterations = 0;
    const MAX = MISSING[slug].size + 10;
    while (iterations < MAX) {
      const clicked = await page.evaluate(() => {
        const selectors = ['[data-hook="next-item"]','[aria-label="Next Item"]','[aria-label="Next"]','button[title="Next"]'];
        for (const sel of selectors) {
          const btn = document.querySelector(sel);
          if (btn) { btn.click(); return true; }
        }
        const buttons = Array.from(document.querySelectorAll('button,[role="button"]'));
        const right = buttons.find(b => {
          const r = b.getBoundingClientRect();
          return r.left > window.innerWidth * 0.7 && r.top > 100 && r.top < window.innerHeight - 100;
        });
        if (right) { right.click(); return true; }
        return false;
      });
      if (!clicked) await page.keyboard.press('ArrowRight');
      await page.waitForTimeout(600);
      iterations++;
      if (captured.size >= MISSING[slug].size) break;
    }
    await page.keyboard.press('Escape');
    await page.waitForTimeout(500);
  }

  await page.waitForTimeout(2000);
  await page.close();

  console.log(`Captured ${captured.size} images for ${slug}`);
  return captured;
}

(async () => {
  const browser = await chromium.launch({ headless: true, args: ['--no-sandbox'] });

  const targets = [
    { slug: 'pleasanton-custom', url: 'https://www.ridgecrestdesigns.com/pleasantoncustomhome' },
    { slug: 'pleasanton-cottage-kitchen', url: 'https://www.ridgecrestdesigns.com/pleasanton-cottage-kitchen' },
  ];

  let totalCaptured = 0, totalUploaded = 0, totalFailed = 0;

  for (const { slug, url } of targets) {
    if (!MISSING[slug] || MISSING[slug].size === 0) {
      console.log(`\nSkipping ${slug} — no missing images`);
      continue;
    }

    const captured = await processProject(browser, url, slug);

    // Save + upload each captured image
    for (const [base, { data, url: srcUrl, ct }] of captured.entries()) {
      const ext = ct.includes('webp') ? 'webp' : 'jpg';
      const filename = `${base}_mv2.${ext}`;
      const tmpPath = path.join('/tmp', filename);
      fs.writeFileSync(tmpPath, data);

      process.stdout.write(`  Uploading ${filename} to ${slug}... `);
      try {
        const res = await uploadToGallery(slug, tmpPath, filename);
        if (res.ok || res.filename) {
          console.log(`OK (gallery count: ${res.gallery_count || '?'})`);
          totalUploaded++;
        } else if (res.note === 'already in gallery') {
          console.log(`already in gallery`);
          totalUploaded++;
        } else {
          console.log(`FAILED: ${JSON.stringify(res)}`);
          totalFailed++;
        }
        fs.unlinkSync(tmpPath);
      } catch(e) {
        console.log(`ERROR: ${e.message}`);
        totalFailed++;
      }
      totalCaptured++;
    }

    // Report what's still missing
    const stillMissing = [...MISSING[slug]].filter(h => !captured.has(h));
    if (stillMissing.length > 0) {
      console.log(`\n  Still missing for ${slug} (${stillMissing.length}):`);
      stillMissing.forEach(h => console.log(`    ${h}`));
    }
  }

  await browser.close();

  console.log('\n' + '='.repeat(60));
  console.log(`DONE. Captured: ${totalCaptured}, Uploaded: ${totalUploaded}, Failed: ${totalFailed}`);
})().catch(e => { console.error('Fatal:', e.message); process.exit(1); });
