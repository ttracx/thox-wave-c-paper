/* Render the Wave C v0.5.0 PDF: cover (no furniture) + body (running
 * header/footer per Template v1.0), merged with pdfunite.
 * Run: NODE_PATH=<playwright node_modules> node wp/pdf.cjs
 */
const { chromium } = require("playwright-core");
const { execFileSync } = require('child_process');
const path = require('path');

const WP = __dirname;
const DIST = path.join(WP, '..', 'dist');
const OUT = path.join(DIST, 'THOX_Wave_C_Flagship_Program_Whitepaper_v0.5.0.pdf');

const header = `<div style="width:100%;font-size:7.5px;color:#6B7280;font-family:Inter,sans-serif;padding:0 0.6in;display:flex;justify-content:space-between;">
<span>Flagships for Every Device: The Wave C Training Program</span>
<span>THOX.ai Research &middot; preprint, not peer reviewed</span></div>`;
const footer = `<div style="width:100%;font-size:7.5px;color:#6B7280;font-family:Inter,sans-serif;padding:0 0.6in;display:flex;justify-content:space-between;">
<span>Your AI. Your Data. Your Rules.&trade;</span>
<span>Page <span class="pageNumber"></span> of <span class="totalPages"></span></span></div>`;

(async () => {
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_BIN });
  const page = await browser.newPage();
  // emulateMedia removed: it flipped print layout to screen in this Chromium build
  await page.goto('file://' + path.join(WP, 'cover.html'), { waitUntil: 'networkidle' });
  await page.pdf({ path: path.join(WP, 'cover.pdf'), format: 'Letter', printBackground: true,
                   margin: { top: '0', bottom: '0', left: '0', right: '0' } });
  await page.goto('file://' + path.join(WP, 'body.html'), { waitUntil: 'networkidle' });
  await page.pdf({ path: path.join(WP, 'body.pdf'), format: 'Letter', printBackground: true,
                   displayHeaderFooter: true, headerTemplate: header, footerTemplate: footer,
                   margin: { top: '0.55in', bottom: '0.55in', left: '0', right: '0' } });
  await browser.close();
  execFileSync('pdfunite', [path.join(WP, 'cover.pdf'), path.join(WP, 'body.pdf'), OUT]);
  console.log('wrote', OUT);
})().catch(e => { console.error(e); process.exit(1); });
