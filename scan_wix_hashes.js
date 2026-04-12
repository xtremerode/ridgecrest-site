/**
 * scan_wix_hashes.js
 * Deep scan of all 18 Wix project pages via network interception.
 * Outputs: /tmp/wix_scan_results.json
 *   { slug: { wixHashes: [...] } }
 */
const { chromium } = require('/home/claudeuser/.npm/_npx/e41f203b7505f1fb/node_modules/playwright');
const fs = require('fs');

const LOGO = 'ff5b18_39307a9fb5f448aa8699880d142bb1fe';

const PROJECTS = [
  { slug: 'alamo-luxury',               wix: 'alamoluxury'                  },
  { slug: 'castro-valley-villa',        wix: 'castro-valley-villa'          },
  { slug: 'danville-dream',             wix: 'danvilledreamhome'            },
  { slug: 'danville-hilltop',           wix: 'danvillehilltophideaway'      },
  { slug: 'lafayette-bistro',           wix: 'lafayette-modern-bistro'      },
  { slug: 'lafayette-luxury',           wix: 'lafayette-laid-back-luxury'   },
  { slug: 'lakeside-cozy-cabin',        wix: 'lakeside-cozy-cabin'          },
  { slug: 'livermore-farmhouse-chic',   wix: 'livermorefarmhousechic'       },
  { slug: 'napa-retreat',               wix: 'naparetreat'                  },
  { slug: 'newark-minimal-kitchen',     wix: 'newarkminimalkitchen'         },
  { slug: 'orinda-kitchen',             wix: 'orinda'                       },
  { slug: 'pleasanton-cottage-kitchen', wix: 'pleasantoncottagekitchen'     },
  { slug: 'pleasanton-custom',          wix: 'pleasantoncustomhome'         },
  { slug: 'pleasanton-garage',          wix: 'pleasanton-garage-renovation' },
  { slug: 'san-ramon',                  wix: 'sanramon'                     },
  { slug: 'san-ramon-eclectic-bath',    wix: 'san-ramon-eclectic-bath'      },
  { slug: 'sierra-mountain-ranch',      wix: 'sierramountainranch'          },
  { slug: 'sunol-homestead',            wix: 'sunolhomestead'               },
];

function extractHash(url) {
  const m = url.match(/ff5b18_([0-9a-f]{32})/i);
  return m ? 'ff5b18_' + m[1] : null;
}

async function scanProject(page, proj) {
  const url = 'https://www.ridgecrestdesigns.com/' + proj.wix;
  const hashes = new Set();

  const handler = async (resp) => {
    const u = resp.url();
    if (u.includes('wixstatic.com/media/ff5b18_')) {
      const h = extractHash(u);
      if (h && h !== LOGO) hashes.add(h);
    }
    const ct = resp.headers()['content-type'] || '';
    if (ct.includes('json') || ct.includes('javascript') || ct.includes('text')) {
      try {
        const text = await resp.text();
        if (!text.includes('ff5b18_')) return;
        const re = /ff5b18_([0-9a-f]{32})/gi;
        let m;
        while ((m = re.exec(text)) !== null) {
          const h = 'ff5b18_' + m[1];
          if (h !== LOGO) hashes.add(h);
        }
      } catch(e) {}
    }
  };
  page.on('response', handler);

  try {
    await page.goto(url, { waitUntil: 'networkidle', timeout: 90000 });
    await page.waitForTimeout(3000);
    let prevH = 0;
    for (let attempt = 0; attempt < 8; attempt++) {
      const h = await page.evaluate(() => document.body.scrollHeight);
      for (let y = prevH; y <= h; y += 300) {
        await page.evaluate(yy => window.scrollTo(0, yy), y);
        await page.waitForTimeout(80);
      }
      prevH = h;
      await page.waitForTimeout(1500);
      const newH = await page.evaluate(() => document.body.scrollHeight);
      if (newH === h) break;
    }
    await page.waitForTimeout(2000);
  } catch(e) {
    console.log('  ERROR: ' + e.message.substring(0, 100));
  }

  page.off('response', handler);
  return [...hashes].filter(h => /^ff5b18_[0-9a-f]{32}$/.test(h));
}

(async () => {
  const browser = await chromium.launch({ headless: true, args: ['--no-sandbox'] });
  const page = await browser.newPage();
  await page.setViewportSize({ width: 1440, height: 900 });

  const results = {};

  for (const proj of PROJECTS) {
    process.stdout.write('[' + proj.slug + '] scanning... ');
    const hashes = await scanProject(page, proj);
    results[proj.slug] = { wixHashes: hashes };
    console.log(hashes.length + ' hashes found');
  }

  await browser.close();

  fs.writeFileSync('/tmp/wix_scan_results.json', JSON.stringify(results, null, 2));
  console.log('\nScan complete. Results saved to /tmp/wix_scan_results.json');
})().catch(e => { console.error('Fatal:', e.message); process.exit(1); });
