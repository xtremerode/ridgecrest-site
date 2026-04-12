/**
 * Deep scan of all 18 project pages — network interception captures ALL image hashes.
 * Compares against on-disk files and outputs per-project missing lists + bat files.
 */
const { chromium } = require('/home/claudeuser/.npm/_npx/e41f203b7505f1fb/node_modules/playwright');
const fs = require('fs');

const LOGO = 'ff5b18_39307a9fb5f448aa8699880d142bb1fe';
const OPT  = '/home/claudeuser/agent/preview/assets/images-opt';
const TOKEN = '35e8bdf6f9cddb3a140a3ac34a9dcb3963c7bff434ef8bd6fedfda70299b13f1';
const SERVER = 'http://147.182.242.54:8081';

const onDisk = new Set(
  fs.readdirSync(OPT)
    .filter(f => f.startsWith('ff5b18_') && f.endsWith('.webp') && !f.includes('_ai_') && !/_\d+w\.webp$/.test(f))
    .map(f => f.replace('.webp', '').replace(/_mv2$/, ''))
);
console.log('Images on disk: ' + onDisk.size);

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

  // Network interception
  const handler = async (resp) => {
    const u = resp.url();
    if (u.includes('wixstatic.com/media/ff5b18_')) {
      const h = extractHash(u);
      if (h && h !== 'ff5b18_' + LOGO.slice(7)) hashes.add(h);
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
          if (h !== 'ff5b18_' + LOGO.slice(7)) hashes.add(h);
        }
      } catch(e) {}
    }
  };
  page.on('response', handler);

  try {
    await page.goto(url, { waitUntil: 'networkidle', timeout: 90000 });
    await page.waitForTimeout(3000);

    // Full scroll to trigger lazy loads
    let prevH = 0;
    for (let attempt = 0; attempt < 6; attempt++) {
      const h = await page.evaluate(() => document.body.scrollHeight);
      for (let y = prevH; y <= h; y += 300) {
        await page.evaluate(yy => window.scrollTo(0, yy), y);
        await page.waitForTimeout(100);
      }
      prevH = h;
      await page.waitForTimeout(1500);
      const newH = await page.evaluate(() => document.body.scrollHeight);
      if (newH === h) break;
    }
    await page.waitForTimeout(2000);
  } catch(e) {
    console.log('  ERROR: ' + e.message.substring(0, 80));
  }

  page.off('response', handler);
  return [...hashes].filter(h => h.length <= 39); // filter malformed
}

function makeBat(slug, missingHashes) {
  const lines = [
    '@echo off',
    'setlocal enabledelayedexpansion',
    `echo Fetching ${missingHashes.length} missing images for ${slug}...`,
    'echo.',
    `set SERVER=http://147.182.242.54:8081`,
    `set TOKEN=${TOKEN}`,
    `set SLUG=${slug}`,
    'set UPLOAD_URL=%SERVER%/admin/api/gallery/%SLUG%/add-image',
    `set TMPDIR=%TEMP%\\${slug}_missing`,
    'set OK=0',
    'set FAIL=0',
    '',
    'if not exist "%TMPDIR%" mkdir "%TMPDIR%"',
    '',
  ];
  for (const h of missingHashes) {
    lines.push(`call :upload ${h}`);
  }
  lines.push('', 'echo.', 'echo Done. %OK% uploaded, %FAIL% failed.', 'rmdir /s /q "%TMPDIR%" 2>nul', 'pause', 'goto :eof', '', ':upload');
  lines.push('set HASH=%1');
  lines.push('set LOCALFILE=%TMPDIR%\\%HASH%_mv2.jpg');
  lines.push('echo Downloading %HASH%...');
  lines.push('curl.exe -s -L -o "%LOCALFILE%" "https://static.wixstatic.com/media/%HASH%~mv2.jpg"');
  lines.push('if not exist "%LOCALFILE%" ( echo   FAILED: download empty & set /a FAIL+=1 & goto :eof )');
  lines.push('curl.exe -s -X POST "%UPLOAD_URL%" -H "X-Admin-Token: %TOKEN%" -F "file=@%LOCALFILE%;filename=%HASH%_mv2.jpg;type=image/jpeg"');
  lines.push('echo   OK');
  lines.push('set /a OK+=1');
  lines.push('del "%LOCALFILE%" 2>nul');
  lines.push('goto :eof');
  return lines.join('\n');
}

(async () => {
  const browser = await chromium.launch({ headless: true, args: ['--no-sandbox'] });
  const page = await browser.newPage();
  await page.setViewportSize({ width: 1440, height: 900 });

  const summary = [];
  const allMissing = [];

  for (const proj of PROJECTS) {
    process.stdout.write('[' + proj.slug + '] scanning... ');
    const hashes = await scanProject(page, proj);
    const missing = hashes.filter(h => !onDisk.has(h));
    console.log(hashes.length + ' found, ' + missing.length + ' missing');
    summary.push({ slug: proj.slug, found: hashes.length, missing: missing.length });
    if (missing.length > 0) {
      allMissing.push(...missing.map(h => ({ slug: proj.slug, hash: h })));
      // Write per-project bat file
      const bat = makeBat(proj.slug, missing);
      fs.writeFileSync(`/home/claudeuser/agent/preview/assets/fetch_${proj.slug.replace(/-/g,'_')}_missing.bat`, bat);
    }
  }

  await browser.close();

  // Print summary table
  console.log('\n' + '='.repeat(55));
  console.log('Project'.padEnd(32) + 'Found'.padStart(7) + 'Missing'.padStart(9));
  console.log('='.repeat(55));
  let tFound = 0, tMissing = 0;
  for (const r of summary) {
    console.log(r.slug.padEnd(32) + String(r.found).padStart(7) + String(r.missing).padStart(9));
    tFound += r.found; tMissing += r.missing;
  }
  console.log('='.repeat(55));
  console.log('TOTAL'.padEnd(32) + String(tFound).padStart(7) + String(tMissing).padStart(9));

  fs.writeFileSync('/home/claudeuser/agent/all_missing.json', JSON.stringify(allMissing, null, 2));
  console.log('\n' + allMissing.length + ' total missing hashes saved to all_missing.json');
  console.log('Per-project .bat files written to preview/assets/fetch_*_missing.bat');
})().catch(e => { console.error('Fatal:', e.message); process.exit(1); });
