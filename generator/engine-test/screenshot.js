// Turn the pages make_previews.py wrote into the README's preview images.
//
//     node screenshot.js <page folder> <previews folder>
//
// Needs Playwright for Node (npm install playwright, then npx playwright install chromium).
const fs = require('fs');
const path = require('path');
const { pathToFileURL } = require('url');
const { chromium } = require('playwright');

(async () => {
  const [pages, previews] = process.argv.slice(2);
  if (!pages || !previews) {
    console.error('usage: node screenshot.js <page folder> <previews folder>');
    process.exit(1);
  }
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 800, height: 300 }, deviceScaleFactor: 2 });
  for (const file of fs.readdirSync(pages).filter((name) => name.endsWith('.html'))) {
    await page.goto(pathToFileURL(path.resolve(pages, file)).href);
    const size = await page.evaluate(() => ({ w: document.body.scrollWidth, h: document.body.scrollHeight }));
    await page.setViewportSize({ width: size.w, height: size.h });
    const target = path.join(previews, file.replace(/\.html$/, '.png'));
    await page.screenshot({ path: target, fullPage: true });
    console.log(target);
  }
  await browser.close();
})();
