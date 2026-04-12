/**
 * download_missing_via_playwright.js
 * Uses Playwright (real browser) to download Wix images that block direct server requests.
 * Saves raw image bytes to /tmp/wix_downloads/ for the Python script to process.
 */
const { chromium } = require('/home/claudeuser/.npm/_npx/e41f203b7505f1fb/node_modules/playwright');
const fs = require('fs');
const path = require('path');

const OUT_DIR = '/tmp/wix_downloads';
if (!fs.existsSync(OUT_DIR)) fs.mkdirSync(OUT_DIR, { recursive: true });

const HASHES = [
  "ff5b18_fb13d3b2359f78413ad107f355e430f9","ff5b18_f5e2d1244a02ad4b45bfd23a704d13b1",
  "ff5b18_08d8dac4e3a27c47df39abce050ac573","ff5b18_bd1d0cb4625ee1b00b7b426e3e976cc7",
  "ff5b18_8885f7ff92419bcdbff73bf3f37891a7","ff5b18_58423d1c7470fe24b55a2930c1e06363",
  "ff5b18_5e781097d465071dffb668c0932bd04c","ff5b18_61ed1991484acd5e2d24ab8a17b41e38",
  "ff5b18_0b068dee485acd56a83b820cb6a5d347","ff5b18_693605de9e9e855daff2e291091436b9",
  "ff5b18_b69750b7a5656f396a626c37446ef852","ff5b18_5fff38fdf4152a62fd19e5a590fece6d",
  "ff5b18_772a97f4c6eee15290bbebce936d500a","ff5b18_f52258a7eee8ad639d64d1d791019e0e",
  "ff5b18_efc6822c7e7d2c009ad3e6a286b493f2","ff5b18_4938cae3572722d89b25bba372fd3117",
  "ff5b18_7e0b347d55f68742f4dff90c64ce2959","ff5b18_5e3c1469607d174bc87db6fa41ccc6ed",
  "ff5b18_39bf510f37eee923698067796469b9aa","ff5b18_ff33e00800168bfe4d94ca4a8ae15e88",
  "ff5b18_96c341602f7e57faad737ff0523f98be","ff5b18_6ec165395655f6597c08621eb9142702",
  "ff5b18_f18c74e8b9a782a3cd5453a12d2174f8","ff5b18_6f6932b21d975b0f87e3a6a6f78f055d",
  "ff5b18_5727bc1abe8e393f6be4db8be695bbdd","ff5b18_95dc5787f236acb1fdc762bc6963e53d",
  "ff5b18_d51f851b312a561107cdddda2b2d20f0","ff5b18_02cc34d6974b2f66e9e6c06d1bc66f4e",
  "ff5b18_d57ecd40640ccf15e5581e4b71e7b383","ff5b18_e7669e01d1a18a9e0b35b4c23a179412",
  "ff5b18_cedd6f07b9b796f7e2c0be46be5621f9","ff5b18_e038d4fe950b3e7968bb154c134d7521",
  "ff5b18_02ec1a01433cf7ae0b117c8ac649fb26","ff5b18_310b18bcf37b98d909bbb440258d60d1",
  "ff5b18_99e750b81be6a6c4565ce1bc2d89fcef","ff5b18_ec6f2d49d7083f3ed43f4fdd76904a8a",
  "ff5b18_f8e20fd87498b99d6769688c1c3422b0","ff5b18_a86b72f67a16a526b05787a493aa53b4",
  "ff5b18_e700a83513d9f58ed050c719702bc661","ff5b18_6ca95f02fa49ab6316e9560de4333aac",
  "ff5b18_3574a2d1d31f2c5396d9a95ce661c0cf","ff5b18_f99126ba9dd29ecfc95b3b52b3942885",
  "ff5b18_beb1c1e39c354dc958a6a5c25587e09f","ff5b18_3838ef51caaa71ec287d555db1e167b8",
  "ff5b18_389c2314b4e8678722c6d8eac8a62e0c","ff5b18_3c34d4072ce363457f88f86e2bee5338",
  "ff5b18_0d032d07e3c5dda7f1cdeb864c1ada6c","ff5b18_e421e99013aa794a231c8774881f9afb",
  "ff5b18_d3adf5e64eeadf0816739ca2c5f634f2","ff5b18_98f97a76f69c41dca1e0ddb7a927be32",
];

(async () => {
  const browser = await chromium.launch({ headless: true, args: ['--no-sandbox'] });
  const context = await browser.newContext({
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
  });

  let ok = 0, failed = [];

  for (const hash of HASHES) {
    let downloaded = false;
    for (const ext of ['jpg', 'png', 'webp']) {
      const url = `https://static.wixstatic.com/media/${hash}~mv2.${ext}`;
      const outFile = path.join(OUT_DIR, `${hash}_mv2.${ext}`);
      try {
        const resp = await context.request.get(url, { timeout: 30000 });
        if (resp.ok()) {
          const body = await resp.body();
          if (body.length > 5000) {
            fs.writeFileSync(outFile, body);
            console.log(`  ✓ ${hash.slice(0,24)}... (${ext}, ${Math.round(body.length/1024)}KB)`);
            ok++;
            downloaded = true;
            break;
          }
        }
      } catch(e) {}
    }
    if (!downloaded) {
      console.log(`  ✗ ${hash.slice(0,24)}...`);
      failed.push(hash);
    }
  }

  await browser.close();
  fs.writeFileSync('/tmp/wix_downloads/results.json', JSON.stringify({ ok, failed }, null, 2));
  console.log(`\nDone: ${ok} downloaded, ${failed.length} failed`);
})().catch(e => { console.error('Fatal:', e.message); process.exit(1); });
