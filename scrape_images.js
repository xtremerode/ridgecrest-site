const { chromium } = require('playwright');

const knownSlugs = [
  'danvilledreamhome',
  'lafayette-modern-bistro',
  'pleasantoncustomhome',
  'sunolhomestead',
  'naparetreat',
  'livermorefarmhousechic',
  'danvillehilltophideaway',
  'sierramountainranch',
  'therdedit',
  // Additional known from portfolio page scrape
  // Try more possible slugs
  'walnutcreekremodel',
  'dublinestates',
  'orindahideaway',
  'alamo-custom',
  'alamocustom',
  'lafayettemodern',
  'san-ramon',
  'sanramon',
  'diablo-custom',
  'diablocustom',
];

async function extractImagesFromPage(page, url) {
  try {
    await page.goto(url, { waitUntil: 'networkidle', timeout: 45000 });
    await page.waitForTimeout(3000);

    // Scroll through the page to trigger lazy loading
    await page.evaluate(async () => {
      for (let i = 0; i < 15; i++) {
        window.scrollBy(0, 600);
        await new Promise(r => setTimeout(r, 400));
      }
      window.scrollTo(0, 0);
    });
    await page.waitForTimeout(2000);

    // Get page title
    const title = await page.title();

    // Get all image URLs from img tags
    const imgSrcs = await page.$$eval('img', imgs => imgs.map(img => ({
      src: img.src,
      dataSrc: img.getAttribute('data-src'),
      srcset: img.getAttribute('srcset'),
      alt: img.alt
    })));

    // Get background images from style attributes
    const bgImages = await page.evaluate(() => {
      const results = [];
      const allElements = document.querySelectorAll('*');
      allElements.forEach(el => {
        const style = el.getAttribute('style');
        if (style && style.includes('background')) {
          results.push(style);
        }
        const computedBg = window.getComputedStyle(el).backgroundImage;
        if (computedBg && computedBg !== 'none' && computedBg.includes('url(')) {
          results.push(computedBg);
        }
      });
      return results;
    });

    // Get all wixstatic URLs from page source
    const pageContent = await page.content();
    const wixUrls = [];
    const wixRegex = /https?:\/\/[^"'\s]*wixstatic\.com\/[^"'\s]*/g;
    let match;
    while ((match = wixRegex.exec(pageContent)) !== null) {
      let url = match[0].replace(/\\u002F/g, '/').replace(/\\/g, '');
      // Clean up any trailing characters
      url = url.replace(/['")\s]+$/, '');
      if (!wixUrls.includes(url)) {
        wixUrls.push(url);
      }
    }

    return { title, imgSrcs, bgImages, wixUrls, found: true };
  } catch (e) {
    return { title: null, imgSrcs: [], bgImages: [], wixUrls: [], found: false, error: e.message };
  }
}

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();

  // First, get all project links from portfolio and allprojects pages
  const portalPages = [
    'https://www.ridgecrestdesigns.com/portfolio',
    'https://www.ridgecrestdesigns.com/allprojects'
  ];

  let projectUrls = new Set();

  for (const portalUrl of portalPages) {
    console.log(`Scanning portal: ${portalUrl}`);
    try {
      await page.goto(portalUrl, { waitUntil: 'networkidle', timeout: 45000 });
      await page.waitForTimeout(4000);

      // Scroll through the page
      await page.evaluate(async () => {
        for (let i = 0; i < 20; i++) {
          window.scrollBy(0, 500);
          await new Promise(r => setTimeout(r, 300));
        }
      });
      await page.waitForTimeout(3000);

      const links = await page.$$eval('a[href]', els => els.map(e => e.href));
      const filtered = links.filter(l =>
        l.includes('ridgecrestdesigns.com') &&
        !l.endsWith('/portfolio') &&
        !l.endsWith('/allprojects') &&
        !l.includes('/california-process') &&
        !l.includes('/testimonials') &&
        !l.includes('/contact') &&
        !l.includes('/about') &&
        !l.includes('/services') &&
        !l.includes('/blog') &&
        !l.includes('#') &&
        !l.includes('?') &&
        l !== 'https://www.ridgecrestdesigns.com/' &&
        l !== 'http://www.ridgecrestdesigns.com/'
      );
      filtered.forEach(l => projectUrls.add(l));
      console.log(`  Found ${filtered.length} project-like links`);
    } catch(e) {
      console.log(`  Error: ${e.message}`);
    }
  }

  // Add known slugs
  knownSlugs.forEach(slug => {
    projectUrls.add(`https://www.ridgecrestdesigns.com/${slug}`);
  });

  console.log(`\nTotal URLs to check: ${projectUrls.size}`);

  const results = {};

  for (const url of projectUrls) {
    const slug = url.split('/').pop();
    console.log(`\nScraping: ${url}`);
    const data = await extractImagesFromPage(page, url);

    if (data.found && data.wixUrls.length > 0) {
      // Filter to only image URLs
      const imageUrls = data.wixUrls.filter(u =>
        u.includes('/media/') &&
        (u.match(/\.(jpg|jpeg|png|gif|webp|svg)/i) || u.includes('~mv2'))
      );

      if (imageUrls.length > 0) {
        results[slug] = {
          url,
          title: data.title,
          images: [...new Set(imageUrls)]
        };
        console.log(`  Title: ${data.title}`);
        console.log(`  Found ${imageUrls.length} image URLs`);
      } else {
        console.log(`  Title: ${data.title} — No images found (${data.wixUrls.length} wix URLs, but none are images)`);
      }
    } else if (!data.found) {
      console.log(`  Page not found or error: ${data.error}`);
    } else {
      console.log(`  Title: ${data.title} — No wixstatic image URLs found`);
    }
  }

  console.log('\n\n========== FINAL RESULTS ==========\n');
  for (const [slug, data] of Object.entries(results)) {
    console.log(`PROJECT: ${data.title} (${data.url})`);
    for (const img of data.images) {
      console.log(`  - ${img}`);
    }
    console.log('');
  }

  // Save results to file
  const fs = require('fs');
  fs.writeFileSync('/home/claudeuser/agent/portfolio_images.json', JSON.stringify(results, null, 2));
  console.log('\nResults saved to /home/claudeuser/agent/portfolio_images.json');

  await browser.close();
})().catch(e => {
  console.error('Fatal error:', e.message);
  process.exit(1);
});
