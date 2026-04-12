/**
 * Lightbox audit — opens each Wix project page, clicks into the gallery lightbox,
 * navigates through every image, and captures all hashes.
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

// gallery_json counts from DB (ours)
const OUR_COUNTS = {
  'alamo-luxury': 7, 'castro-valley-villa': 9, 'danville-dream': 16,
  'danville-hilltop': 19, 'lafayette-bistro': 6, 'lafayette-luxury': 20,
  'lakeside-cozy-cabin': 13, 'livermore-farmhouse-chic': 6, 'napa-retreat': 33,
  'newark-minimal-kitchen': 4, 'orinda-kitchen': 14, 'pleasanton-cottage-kitchen': 3,
  'pleasanton-custom': 58, 'pleasanton-garage': 6, 'san-ramon': 6,
  'san-ramon-eclectic-bath': 5, 'sierra-mountain-ranch': 27, 'sunol-homestead': 37,
};

const PROJECTS = [
  { slug: 'alamo-luxury',               wix: 'alamoluxury',                 oldCount: 7  },
  { slug: 'castro-valley-villa',        wix: 'castro-valley-villa',         oldCount: 8  },
  { slug: 'danville-dream',             wix: 'danvilledreamhome',           oldCount: 16 },
  { slug: 'danville-hilltop',           wix: 'danvillehilltophideaway',     oldCount: 19 },
  { slug: 'lafayette-bistro',           wix: 'lafayette-modern-bistro',     oldCount: 5  },
  { slug: 'lafayette-luxury',           wix: 'lafayette-laid-back-luxury',  oldCount: 19 },
  { slug: 'lakeside-cozy-cabin',        wix: 'lakeside-cozy-cabin',         oldCount: 11 },
  { slug: 'livermore-farmhouse-chic',   wix: 'livermorefarmhousechic',      oldCount: 6  },
  { slug: 'napa-retreat',               wix: 'naparetreat',                 oldCount: 46 },
  { slug: 'newark-minimal-kitchen',     wix: 'newarkminimalkitchen',        oldCount: 0  },
  { slug: 'orinda-kitchen',             wix: 'orinda',                      oldCount: 14 },
  { slug: 'pleasanton-cottage-kitchen', wix: 'pleasantoncottagekitchen',    oldCount: 4  },
  { slug: 'pleasanton-custom',          wix: 'pleasantoncustomhome',        oldCount: 59 },
  { slug: 'pleasanton-garage',          wix: 'pleasanton-garage-renovation',oldCount: 5  },
  { slug: 'san-ramon',                  wix: 'sanramon',                    oldCount: 6  },
  { slug: 'san-ramon-eclectic-bath',    wix: 'san-ramon-eclectic-bath',     oldCount: 4  },
  { slug: 'sierra-mountain-ranch',      wix: 'sierramountainranch',         oldCount: 25 },
  { slug: 'sunol-homestead',            wix: 'sunolhomestead',              oldCount: 36 },
];

function extractHash(url) {
  if (!url) return null;
  const m = url.match(/ff5b18_([0-9a-f]{30,})/);
  return m ? 'ff5b18_' + m[1] : null;
}

async function auditProject(page, proj) {
  const url = 'https://www.ridgecrestdesigns.com/' + proj.wix;
  const hashes = new Set();
  let method = 'lightbox';

  try {
    await page.goto(url, { waitUntil: 'networkidle', timeout: 60000 });
    await page.waitForTimeout(3000);

    // Scroll through page to load all gallery thumbnails
    const height = await page.evaluate(() => document.body.scrollHeight);
    for (let y = 0; y <= height; y += 400) {
      await page.evaluate((yy) => window.scrollTo(0, yy), y);
      await page.waitForTimeout(80);
    }
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.waitForTimeout(1500);

    // Try to click the first wixstatic gallery image
    const allImgs = await page.$$('img');
    let clicked = false;
    for (const img of allImgs) {
      const src = await img.getAttribute('src') || '';
      if (src.includes('wixstatic.com/media/ff5b18_') && !src.includes(LOGO)) {
        try {
          await img.scrollIntoViewIfNeeded();
          await img.click({ timeout: 3000 });
          clicked = true;
          break;
        } catch(e) {}
      }
    }

    if (!clicked) {
      // Fallback: collect from page source only
      method = 'source';
      const html = await page.content();
      const re = /ff5b18_([0-9a-f]{30,})/g;
      let m;
      while ((m = re.exec(html)) !== null) {
        const h = 'ff5b18_' + m[1];
        if (!h.includes(LOGO)) hashes.add(h);
      }
      return { hashes: [...hashes], method, error: 'could not click gallery image' };
    }

    await page.waitForTimeout(2000);

    // Detect if lightbox is open by looking for a dialog or large image
    const lbImgSel = '[role="dialog"] img, [aria-modal="true"] img, [data-hook="lightbox"] img';
    const lbVisible = await page.$(lbImgSel).catch(() => null);

    if (!lbVisible) {
      method = 'source';
      const html = await page.content();
      const re = /"mediaUrl"\s*:\s*"(ff5b18_[0-9a-f]+)[~%](?:7E)?mv2\.(jpg|jpeg|png|webp)"/gi;
      let m;
      while ((m = re.exec(html)) !== null) {
        const h = m[1] + '_mv2';
        if (!h.includes(LOGO)) hashes.add(h);
      }
      return { hashes: [...hashes], method, error: 'lightbox not detected' };
    }

    // Navigate through lightbox
    const getHashFromLb = async () => {
      const srcs = await page.$$eval(lbImgSel,
        els => els.map(el => el.src || el.getAttribute('data-src') || '').filter(s => s && s.includes('wixstatic.com/media/ff5b18_'))
      ).catch(() => []);
      return srcs.map(extractHash).filter(h => h && !h.includes(LOGO));
    };

    // Capture first image hash for loop detection
    let firstBatch = await getHashFromLb();
    firstBatch.forEach(h => hashes.add(h));
    const firstHash = firstBatch[0] || null;

    const MAX_NAV = 250;
    let loopDetected = false;

    for (let i = 0; i < MAX_NAV && !loopDetected; i++) {
      // Find next button by common Wix selectors and aria labels
      const nextBtn = await page.$('[data-hook="next-item"]') ||
                      await page.$('[aria-label="Next Item"]') ||
                      await page.$('[aria-label="Next"]') ||
                      await page.$('button[aria-label*="ext"]');

      if (!nextBtn) break;
      await nextBtn.click();
      await page.waitForTimeout(500);

      const curHashes = await getHashFromLb();
      curHashes.forEach(h => hashes.add(h));

      // Loop detection: if we see the first image again after going through enough
      if (i > 3 && firstHash && curHashes.includes(firstHash)) {
        // One more step to confirm it's not a coincidence
        loopDetected = true;
      }
    }

    // Close lightbox
    await page.keyboard.press('Escape');
    await page.waitForTimeout(500);

  } catch(e) {
    return { hashes: [...hashes], method, error: e.message.substring(0, 100) };
  }

  return { hashes: [...hashes], method };
}

(async () => {
  const browser = await chromium.launch({ headless: true, args: ['--no-sandbox'] });
  const page = await browser.newPage();
  await page.setViewportSize({ width: 1440, height: 900 });

  const results = [];

  for (const proj of PROJECTS) {
    process.stdout.write('[' + proj.slug + '] ');
    const { hashes, method, error } = await auditProject(page, proj);
    const lbCount = hashes.length;
    const notOnDisk = hashes.filter(h => !onDisk.has(h));
    console.log(lbCount + ' via ' + method + (error ? ' (' + error + ')' : '') + ' — ' + notOnDisk.length + ' not on disk');
    results.push({ ...proj, lbCount, notOnDisk });
  }

  await browser.close();

  // Print comparison
  console.log('\n' + '='.repeat(72));
  console.log('Project'.padEnd(30) + 'Old(curl)'.padStart(10) + 'New(LB)'.padStart(9) + 'Change'.padStart(8) + 'Ours'.padStart(6) + 'Missing'.padStart(9));
  console.log('='.repeat(72));

  let tOld=0, tNew=0, tOurs=0, tMiss=0;
  for (const r of results) {
    const our = OUR_COUNTS[r.slug] || 0;
    const change = r.lbCount - r.oldCount;
    const miss = r.notOnDisk.length;
    const changeStr = change > 0 ? '+'+change : (change < 0 ? ''+change : '—');
    console.log(
      r.slug.padEnd(30) +
      String(r.oldCount).padStart(10) +
      String(r.lbCount).padStart(9) +
      changeStr.padStart(8) +
      String(our).padStart(6) +
      String(miss).padStart(9)
    );
    tOld += r.oldCount; tNew += r.lbCount; tOurs += our; tMiss += miss;
  }
  console.log('='.repeat(72));
  console.log('TOTAL'.padEnd(30) + String(tOld).padStart(10) + String(tNew).padStart(9) + ''.padStart(8) + String(tOurs).padStart(6) + String(tMiss).padStart(9));

  // Save missing for later
  const allMissing = results.flatMap(r => r.notOnDisk.map(h => ({ slug: r.slug, hash: h })));
  fs.writeFileSync('/home/claudeuser/agent/missing_images.json', JSON.stringify(allMissing, null, 2));
  console.log('\n' + allMissing.length + ' missing hashes saved to missing_images.json');
})().catch(e => { console.error('Fatal:', e.message); process.exit(1); });
