const { chromium } = require('playwright');

const NODE_MODULES = '/home/claudeuser/.npm/_npx/e41f203b7505f1fb/node_modules';

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();

  // First check allprojects page
  const pagesToCheck = [
    'https://www.ridgecrestdesigns.com/allprojects',
    'https://www.ridgecrestdesigns.com/portfolio'
  ];

  let allProjectLinks = new Set();

  for (const url of pagesToCheck) {
    console.log(`\nChecking: ${url}`);
    await page.goto(url, { waitUntil: 'networkidle', timeout: 60000 });
    await page.waitForTimeout(4000);

    // Scroll through the page
    await page.evaluate(async () => {
      for (let i = 0; i < 20; i++) {
        window.scrollBy(0, 600);
        await new Promise(r => setTimeout(r, 400));
      }
    });
    await page.waitForTimeout(3000);

    const links = await page.$$eval('a[href]', els => els.map(e => e.href));
    const filtered = links.filter(l =>
      l.includes('ridgecrestdesigns.com') &&
      !l.includes('/portfolio') &&
      !l.includes('/allprojects') &&
      !l.includes('/california-process') &&
      !l.includes('/testimonials') &&
      !l.includes('/contact') &&
      !l.includes('/about') &&
      !l.includes('/services') &&
      !l.includes('/blog') &&
      !l.includes('#') &&
      l !== 'https://www.ridgecrestdesigns.com/' &&
      l !== 'http://www.ridgecrestdesigns.com/'
    );
    filtered.forEach(l => allProjectLinks.add(l));

    console.log(`Found ${filtered.length} links on this page`);
  }

  console.log('\n=== ALL PROJECT LINKS ===');
  const linkArray = [...allProjectLinks];
  console.log(JSON.stringify(linkArray, null, 2));
  console.log(`Total: ${linkArray.length} project links`);

  await browser.close();
})().catch(e => {
  console.error('Error:', e.message);
  process.exit(1);
});
