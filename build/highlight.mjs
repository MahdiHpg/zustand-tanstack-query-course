// Build-time syntax highlighting: open book-raw.html in Chromium, run highlight.js,
// save the highlighted DOM as build/book.html. Deterministic (no runtime JS in final PDF).
import { createRequire } from 'node:module';
import { execSync } from 'node:child_process';
import path from 'node:path';
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '..');
const RAW = path.join(ROOT, 'build', 'book-raw.html');
const OUT = path.join(ROOT, 'build', 'book.html');
const HLJS = path.join(ROOT, 'vendor', 'highlight.min.js');

const g = execSync('npm root -g').toString().trim();
const requirePw = createRequire(path.join(g, 'playwright', 'package.json'));
const { chromium } = requirePw('playwright');

let browser;
try {
  browser = await chromium.launch({ headless: true });
} catch {
  const chrome = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
  browser = await chromium.launch({ headless: true, executablePath: chrome });
}
const page = await browser.newPage();
await page.goto('file:///' + RAW.replace(/\\/g, '/'), { waitUntil: 'load' });
await page.addScriptTag({ path: HLJS });
const n = await page.evaluate(() => {
  let count = 0;
  document.querySelectorAll('pre code').forEach((el) => {
    if (!el.dataset.hl) {
      try { window.hljs.highlightElement(el); el.dataset.hl = '1'; count++; } catch (e) {}
    }
  });
  return count;
});
fs.writeFileSync(OUT, await page.content(), 'utf-8');
console.log('OK highlighted', n, 'code blocks ->', OUT);
await browser.close();
