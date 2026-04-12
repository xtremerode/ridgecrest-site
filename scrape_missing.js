/**
 * Scrapes only the 9 Wix project pages missing from portfolio_images.json.
 * PNG files are intentionally excluded (caused OOM on prior run).
 */
const { chromium } = require('/home/claudeuser/.npm/_npx/e41f203b7505f1fb/node_modules/playwright');
const fs = require('fs');

const MISSING_SLUGS = [
  'alamoluxury',
  'castro-valley-villa',
  'lafayette-laid-back-luxury',
  'lakeside-cozy-cabin',
  'newarkminimalkitchen',
  'orinda',
  'pleasanton-garage-renovation',
  'pleasantoncottagekitchen',
  'san-ramon-eclectic-bath',
];

async function extractImages(page, url) {
  try {
    await page.goto(url, { waitUntil: 'networkidle', timeout: 45000 });
    await page.waitForTimeout(2000);

    // Scroll to trigger lazy loading
    await page.evaluate(async () => {
      for (let i = 0; i < 15; i++) {
        window.scrollBy(0, 600);
        await new Promise(r => setTimeout(r, 300));
      }
      window.scrollTo(0, 0);
    });
    await page.waitForTimeout(1500);

    const title = await page.title();

    // Extract wixstatic URLs from page source — JPG only, no PNG
    const pageContent = await page.content();
    const wixUrls = [];
    const wixRegex = /https?:\/\/[^"'\s]*wixstatic\.com\/[^"'\s]*/g;
    let match;
    while ((match = wixRegex.exec(pageContent)) !== null) {
      let u = match[0].replace(/\\u002F/g, '/').replace(/\\/g, '').replace(/['")\s]+$/, '');
      if (!wixUrls.includes(u)) wixUrls.push(u);
    }

    const imageUrls = wixUrls.filter(u =>
      u.includes('/media/') &&
      (u.match(/\.(jpg|jpeg|webp|gif)/i) || u.includes('~mv2')) &&
      !u.match(/\.png/i)   // skip PNGs — caused OOM
    );

    return { title, images: [...new Set(imageUrls)], found: imageUrls.length > 0 };
  } catch (e) {
    return { title: null, images: [], found: false, error: e.message };
  }
}

(async () => {
  // Load existing portfolio_images.json
  const outPath = '/home/claudeuser/agent/portfolio_images.json';
  const results = JSON.parse(fs.readFileSync(outPath, 'utf8'));

  const browser = await chromium.launch({ args: ['--no-sandbox'] });
  const page = await browser.newPage();

  for (const slug of MISSING_SLUGS) {
    const url = `https://www.ridgecrestdesigns.com/${slug}`;
    console.log(`\nScraping: ${url}`);

    const data = await extractImages(page, url);

    if (data.found) {
      results[slug] = { url, title: data.title, images: data.images };
      console.log(`  ✓ ${data.title} — ${data.images.length} image URLs`);
    } else {
      console.log(`  ✗ No images found (${data.error || 'zero results'})`);
    }

    // Save after each page so a crash doesn't lose progress
    fs.writeFileSync(outPath, JSON.stringify(results, null, 2));
  }

  await browser.close();

  console.log('\n\nDone. portfolio_images.json updated.');
  const keys = Object.keys(results);
  console.log(`Total projects: ${keys.length}`);
  keys.forEach(k => console.log(`  ${k}: ${results[k].images.length} images`));
})().catch(e => {
  console.error('Fatal:', e.message);
  process.exit(1);
});
