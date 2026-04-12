const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();

  console.log('Navigating to portfolio page...');
  await page.goto('https://www.ridgecrestdesigns.com/portfolio', {
    waitUntil: 'networkidle',
    timeout: 60000
  });
  await page.waitForTimeout(5000);

  // Scroll to trigger lazy loading
  await page.evaluate(async () => {
    for (let i = 0; i < 10; i++) {
      window.scrollBy(0, 800);
      await new Promise(r => setTimeout(r, 500));
    }
  });
  await page.waitForTimeout(3000);

  const links = await page.$$eval('a[href]', els => els.map(e => e.href));
  const projectLinks = [...new Set(links)].filter(l =>
    l.includes('ridgecrestdesigns.com') &&
    !l.includes('/portfolio') &&
    l !== 'https://www.ridgecrestdesigns.com/' &&
    !l.includes('facebook') && !l.includes('instagram') && !l.includes('yelp') &&
    !l.includes('/contact') && !l.includes('/about') && !l.includes('/services') &&
    !l.includes('/blog') && !l.includes('#')
  );

  console.log('Found project links:');
  console.log(JSON.stringify(projectLinks, null, 2));

  await browser.close();
})().catch(e => {
  console.error('Error:', e.message);
  process.exit(1);
});
