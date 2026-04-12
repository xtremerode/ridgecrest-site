const { chromium } = require('playwright');
const fs = require('fs');

const slug = process.argv[2];
if (!slug) {
  console.error('Usage: node scrape_single.js <slug>');
  process.exit(1);
}

const url = slug.startsWith('http') ? slug : `https://www.ridgecrestdesigns.com/${slug}`;

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();

  console.log(`Scraping: ${url}`);
  try {
    // Use domcontentloaded + extra wait to handle slow Wix pages
    await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 90000 });
    await page.waitForTimeout(6000);

    // Scroll to trigger lazy loading
    await page.evaluate(async () => {
      for (let i = 0; i < 20; i++) {
        window.scrollBy(0, 500);
        await new Promise(r => setTimeout(r, 300));
      }
    });
    await page.waitForTimeout(4000);

    const title = await page.title();

    const pageContent = await page.content();
    const wixUrls = [];
    const wixRegex = /https?:\/\/[^"'\s<>]*wixstatic\.com\/[^"'\s<>]*/g;
    let match;
    while ((match = wixRegex.exec(pageContent)) !== null) {
      let u = match[0].replace(/\\u002F/g, '/').replace(/\\/g, '');
      u = u.replace(/['")\]\s]+$/, '');
      if (!wixUrls.includes(u)) wixUrls.push(u);
    }

    const imageUrls = [...new Set(wixUrls.filter(u =>
      u.includes('/media/') &&
      (u.match(/\.(jpg|jpeg|png|gif|webp|svg)/i) || u.includes('~mv2'))
    ))];

    console.log(`Title: ${title}`);
    console.log(`Found ${imageUrls.length} image URLs`);

    // Load existing results
    let existing = {};
    if (fs.existsSync('/home/claudeuser/agent/portfolio_images.json')) {
      existing = JSON.parse(fs.readFileSync('/home/claudeuser/agent/portfolio_images.json', 'utf8'));
    }

    existing[slug] = { url, title, images: imageUrls };
    fs.writeFileSync('/home/claudeuser/agent/portfolio_images.json', JSON.stringify(existing, null, 2));
    console.log('Saved.');
  } catch(e) {
    console.error('Error:', e.message);
  }

  await browser.close();
})();
