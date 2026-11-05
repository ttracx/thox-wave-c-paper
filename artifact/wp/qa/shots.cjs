/* QA renders for the Wave C v0.5.0 pack: desktop + true-390-width
 * screenshots of the paper HTML and the demo, a demo interaction smoke
 * test (open a run, open a question), and horizontal-scroll checks.
 * Run with CHROMIUM_BIN + NODE_PATH set (playwright-core).
 */
const { chromium } = require('playwright-core');
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..', '..');
const DIST = path.join(ROOT, 'dist');
const QA = __dirname;
const PAPER = 'file://' + path.join(DIST, 'THOX_Wave_C_Flagship_Program_Whitepaper_v0.5.0.html');
const DEMO = 'file://' + path.join(DIST, 'WaveC_Demo_v0.5.0.html');

(async () => {
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_BIN });
  const report = {};
  for (const [name, url] of [['paper', PAPER], ['demo', DEMO]]) {
    for (const w of [1280, 390]) {
      const page = await browser.newPage({ viewport: { width: w, height: 900 }, colorScheme: 'light' });
      await page.goto(url, { waitUntil: 'networkidle' });
      const metrics = await page.evaluate(() => ({
        scrollW: document.documentElement.scrollWidth,
        innerW: window.innerWidth,
        title: document.title,
      }));
      report[`${name}-${w}`] = metrics;
      await page.screenshot({ path: path.join(QA, `${name}-${w}.png`) });
      if (name === 'paper' && w === 1280) {
        await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight * 0.45));
        await page.waitForTimeout(300);
        await page.screenshot({ path: path.join(QA, 'paper-1280-mid.png') });
      }
      if (name === 'demo' && w === 1280) {
        // interaction smoke test: pick the last program run, open question 1
        await page.click('#groupSel');
        await page.selectOption('#groupSel', { index: 0 });
        await page.waitForTimeout(200);
        const cards = await page.$$('.run');
        await cards[cards.length - 1].click();
        await page.waitForTimeout(200);
        const cell = await page.$('.q');
        if (cell) await cell.click();
        await page.waitForTimeout(200);
        const out = await page.textContent('#qOut');
        report['demo-interaction'] = (out || '').slice(0, 200);
        await page.screenshot({ path: path.join(QA, 'demo-1280-interaction.png') });
      }
      await page.close();
    }
  }
  await browser.close();
  fs.writeFileSync(path.join(QA, 'render-metrics.json'), JSON.stringify(report, null, 1));
  console.log(JSON.stringify(report, null, 1));
})().catch(e => { console.error(e); process.exit(1); });
