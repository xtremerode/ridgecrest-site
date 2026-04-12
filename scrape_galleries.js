/**
 * Scrapes the exact gallery images from each Wix project page.
 * Extracts hashes from gallery/slideshow/media components — not nav/thumbnails.
 * Saves results to wix_galleries.json
 */
const { chromium } = require('/home/claudeuser/.npm/_npx/e41f203b7505f1fb/node_modules/playwright');
const fs = require('fs');

const PROJECTS = [
  { slug: 'sierra-mountain-ranch',       wixSlug: 'sierramountainranch' },
  { slug: 'pleasanton-custom',           wixSlug: 'pleasantoncustomhome' },
  { slug: 'sunol-homestead',             wixSlug: 'sunolhomestead' },
  { slug: 'danville-hilltop',            wixSlug: 'danvillehilltophideaway' },
  { slug: 'napa-retreat',                wixSlug: 'naparetreat' },
  { slug: 'lafayette-luxury',            wixSlug: 'lafayette-laid-back-luxury' },
  { slug: 'orinda-kitchen',              wixSlug: 'orinda' },
  { slug: 'danville-dream',              wixSlug: 'danvilledreamhome' },
  { slug: 'alamo-luxury',                wixSlug: 'alamoluxury' },
  { slug: 'lafayette-bistro',            wixSlug: 'lafayette-modern-bistro' },
  { slug: 'san-ramon',                   wixSlug: 'sanramon' },
  { slug: 'pleasanton-garage',           wixSlug: 'pleasanton-garage-renovation' },
  { slug: 'livermore-farmhouse-chic',    wixSlug: 'livermorefarmhousechic' },
  { slug: 'pleasanton-cottage-kitchen',  wixSlug: 'pleasantoncottagekitchen' },
  { slug: 'san-ramon-eclectic-bath',     wixSlug: 'san-ramon-eclectic-bath' },
  { slug: 'castro-valley-villa',         wixSlug: 'castro-valley-villa' },
  { slug: 'lakeside-cozy-cabin',         wixSlug: 'lakeside-cozy-cabin' },
  { slug: 'newark-minimal-kitchen',      wixSlug: 'newarkminimalkitchen' },
];

const LOGO_HASH = 'ff5b18_39307a9fb5f448aa8699880d142bb1fe';
// Small UI icon hashes to skip (social icons etc — non-ff5b18 prefix)
const EXCLUDE_PREFIXES = ['11062b_', '6c9eb6_'];

function extractHash(url) {
  const m = url.match(/(ff5b18_[0-9a-f]+)~?_?mv2[._](jpg|jpeg|png|webp)/i);
  if (!m) return null;
  return { hash: m[1] + '_mv2', ext: m[2].toLowerCase() };
}

async function scrapeGallery(page, wixSlug) {
  const url = `https://www.ridgecrestdesigns.com/${wixSlug}`;

  try {
    await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 45000 });
    await page.waitForTimeout(3000);

    // Scroll slowly to trigger lazy-load on all gallery images
    await page.evaluate(async () => {
      const delay = ms => new Promise(r => setTimeout(r, ms));
      const total = document.body.scrollHeight;
      const step = 400;
      for (let y = 0; y < total; y += step) {
        window.scrollTo(0, y);
        await delay(200);
      }
      window.scrollTo(0, 0);
    });
    await page.waitForTimeout(2000);

    const title = await page.title();

    // Strategy 1: Extract from Wix gallery/media containers specifically
    // Wix gallery items are in: [data-mesh-id], wix-image, [data-hook="imageX"], gallery items
    const galleryImages = await page.evaluate(() => {
      const results = [];
      const seen = new Set();

      // Get all img elements with wixstatic src
      document.querySelectorAll('img').forEach(img => {
        const src = img.src || img.getAttribute('data-src') || '';
        if (src.includes('wixstatic.com/media/ff5b18_')) {
          // Filter out tiny thumbnails (< 100px) and nav images
          const rect = img.getBoundingClientRect();
          const nat = { w: img.naturalWidth, h: img.naturalHeight };
          // Accept images that are reasonably sized in the DOM or have srcset suggesting gallery
          const srcset = img.getAttribute('srcset') || img.getAttribute('data-srcset') || '';
          const hasLargeSrcset = srcset.includes('980') || srcset.includes('1280') || srcset.includes('1920') || srcset.includes('1600');
          const isLargeNatural = nat.w > 300 && nat.h > 200;
          const isLargeInDom = (img.offsetWidth > 250 || img.offsetHeight > 180);

          if ((hasLargeSrcset || isLargeNatural || isLargeInDom) && !seen.has(src)) {
            seen.add(src);
            results.push({ src, width: img.offsetWidth, height: img.offsetHeight, naturalW: nat.w, naturalH: nat.h });
          }
        }
      });

      // Also extract from background-image styles
      document.querySelectorAll('[style]').forEach(el => {
        const style = el.getAttribute('style') || '';
        const bg = el.style.backgroundImage || '';
        const combined = style + bg;
        const m = combined.match(/url\("?([^"')]*wixstatic\.com\/media\/ff5b18_[^"')]+)"?\)/);
        if (m && !seen.has(m[1])) {
          // Only reasonably sized containers
          if (el.offsetWidth > 250 || el.offsetHeight > 180) {
            seen.add(m[1]);
            results.push({ src: m[1], width: el.offsetWidth, height: el.offsetHeight, naturalW: 0, naturalH: 0 });
          }
        }
      });

      return results;
    });

    // Strategy 2: Also get ALL wixstatic URLs from page source
    const pageContent = await page.content();
    const allWixUrls = [];
    const wixRegex = /https?:\/\/static\.wixstatic\.com\/media\/ff5b18_[0-9a-f]+~mv2\.[a-z]+/gi;
    let m;
    while ((m = wixRegex.exec(pageContent)) !== null) {
      allWixUrls.push(m[0]);
    }

    // Also extract from JSON data embedded in page (Wix stores image data as JSON)
    const jsonMatches = pageContent.match(/"uri"\s*:\s*"(ff5b18_[0-9a-f]+_mv2\.(jpg|jpeg|png|webp))"/gi) || [];
    const jsonUris = jsonMatches.map(s => {
      const inner = s.match(/"uri"\s*:\s*"([^"]+)"/);
      return inner ? inner[1] : null;
    }).filter(Boolean);

    return { title, galleryImages, allWixUrls, jsonUris, found: true };
  } catch(e) {
    return { title: null, galleryImages: [], allWixUrls: [], jsonUris: [], found: false, error: e.message };
  }
}

(async () => {
  const outPath = '/home/claudeuser/agent/wix_galleries.json';
  const existing = fs.existsSync(outPath) ? JSON.parse(fs.readFileSync(outPath)) : {};

  const browser = await chromium.launch({ args: ['--no-sandbox'] });
  const page = await browser.newPage();
  await page.setViewportSize({ width: 1440, height: 900 });

  const results = { ...existing };

  for (const proj of PROJECTS) {
    if (results[proj.slug] && results[proj.slug].done) {
      console.log(`  SKIP ${proj.slug} (already scraped)`);
      continue;
    }

    console.log(`\nScraping: ${proj.wixSlug} → ${proj.slug}`);
    const data = await scrapeGallery(page, proj.wixSlug);

    if (!data.found) {
      console.log(`  ERROR: ${data.error}`);
      // Try once more
      const retry = await scrapeGallery(page, proj.wixSlug);
      if (!retry.found) {
        console.log(`  RETRY FAILED — skipping`);
        results[proj.slug] = { done: true, images: [], error: data.error };
        fs.writeFileSync(outPath, JSON.stringify(results, null, 2));
        continue;
      }
      Object.assign(data, retry);
    }

    // Build deduplicated hash list from all sources
    const seen = new Set();
    const images = [];

    // From gallery elements (most reliable — these are actually visible images)
    for (const img of data.galleryImages) {
      const h = extractHash(img.src);
      if (h && h.hash !== LOGO_HASH + '_mv2' && !seen.has(h.hash)) {
        seen.add(h.hash);
        images.push({ ...h, source: 'dom', domW: img.width, domH: img.height });
      }
    }

    // From page source URLs
    for (const url of data.allWixUrls) {
      const h = extractHash(url);
      if (h && h.hash.replace('_mv2','') !== LOGO_HASH && !seen.has(h.hash)) {
        seen.add(h.hash);
        images.push({ ...h, source: 'source' });
      }
    }

    // From JSON URIs embedded in page data
    for (const uri of data.jsonUris) {
      const cleaned = uri.replace('~mv2', '_mv2').replace(/~mv2/, '_mv2');
      const m2 = cleaned.match(/(ff5b18_[0-9a-f]+_mv2)\.(jpg|jpeg|png|webp)/i);
      if (m2) {
        const hash = m2[1];
        const ext = m2[2].toLowerCase();
        if (hash.replace('_mv2','') !== LOGO_HASH && !seen.has(hash)) {
          seen.add(hash);
          images.push({ hash, ext, source: 'json' });
        }
      }
    }

    results[proj.slug] = {
      done: true,
      wixSlug: proj.wixSlug,
      title: data.title,
      images,
      domCount: data.galleryImages.length,
      sourceCount: data.allWixUrls.length,
    };

    console.log(`  ✓ ${data.title}`);
    console.log(`    DOM images: ${data.galleryImages.length}, Source URLs: ${data.allWixUrls.length}, JSON URIs: ${data.jsonUris.length}`);
    console.log(`    Unique images: ${images.length}`);

    fs.writeFileSync(outPath, JSON.stringify(results, null, 2));
    await page.waitForTimeout(1000);
  }

  await browser.close();
  console.log('\n\nDone. Results saved to wix_galleries.json');

  for (const [slug, d] of Object.entries(results)) {
    console.log(`  ${slug}: ${d.images ? d.images.length : 0} images`);
  }
})().catch(e => {
  console.error('Fatal:', e.message);
  process.exit(1);
});
