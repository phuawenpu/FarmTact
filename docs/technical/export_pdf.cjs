// Print a trusted local report with no network access.
// Usage: node export_pdf.cjs /path/to/puppeteer input.html output.pdf evidence.json
const fs = require('node:fs');
const path = require('node:path');
const { pathToFileURL } = require('node:url');
const puppeteer = require(path.resolve(process.argv[2]));
(async () => {
  const input = path.resolve(process.argv[3]);
  const output = path.resolve(process.argv[4]);
  const evidence = path.resolve(process.argv[5]);
  const browser = await puppeteer.launch({headless:true,args:['--no-sandbox']});
  try {
    const page = await browser.newPage();
    await page.setViewport({width:1440,height:1100});
    const external = [];
    await page.setRequestInterception(true);
    page.on('request', request => {
      if (request.url().startsWith('file:') || request.url().startsWith('data:')) request.continue();
      else { external.push(request.url()); request.abort(); }
    });
    await page.goto(pathToFileURL(input).href, {waitUntil:'load'});
    await page.evaluate(() => document.fonts.ready);
    const result = await page.evaluate(() => ({
      title:document.title,
      chapters:document.querySelectorAll('article').length,
      images:document.images.length,
      brokenImages:[...document.images].filter(i => !i.complete || !i.naturalWidth).map(i => i.alt),
      equations:document.querySelectorAll('mjx-container').length,
      brokenAnchors:[...document.querySelectorAll('a[href^="#"]')].map(a => a.getAttribute('href')).filter(h => !document.getElementById(decodeURIComponent(h.slice(1)))) ,
      horizontalPageOverflow:document.documentElement.scrollWidth > window.innerWidth,
    }));
    result.blockedExternalRequests=external;
    if (result.brokenImages.length || result.brokenAnchors.length || external.length || result.horizontalPageOverflow) {
      fs.writeFileSync(evidence, JSON.stringify(result,null,2)+'\n');
      throw new Error('Report render checks failed; inspect evidence JSON.');
    }
    await page.screenshot({path:output.replace(/\.pdf$/,'.preview.png')});
    await page.pdf({path:output,format:'A4',printBackground:true,margin:{top:'14mm',bottom:'14mm',left:'12mm',right:'12mm'},displayHeaderFooter:true,headerTemplate:'<span></span>',footerTemplate:'<div style="font:8px sans-serif;width:100%;text-align:center">FarmTact implementation audit · 11 September 2026 · <span class="pageNumber"></span> / <span class="totalPages"></span></div>'});
    result.status='PASS';
    fs.writeFileSync(evidence,JSON.stringify(result,null,2)+'\n');
    process.stdout.write(JSON.stringify(result,null,2)+'\n');
  } finally { await browser.close(); }
})().catch(error => {process.stderr.write(error.message+'\n');process.exitCode=1;});
