// Only synthetic labels are entered. Real human review packets remain empty.
const {chromium}=require(process.env.HALITE_PLAYWRIGHT_MODULE||'playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {pathToFileURL}=require('node:url');
(async()=>{
 const directory=process.env.HALITE_REVIEW_EVIDENCE_DIR||'/tmp/halite-grounding-review-browser';fs.mkdirSync(directory,{recursive:true});
 const browser=await chromium.launch({executablePath:'/usr/bin/google-chrome',headless:true,args:['--no-sandbox']});
 const page=await browser.newPage({viewport:{width:1100,height:900}});const errors=[];page.on('pageerror',e=>errors.push(e.message));
 async function download(button,name){const pending=page.waitForEvent('download');await page.locator(button).click();await(await pending).saveAs(path.join(directory,name));return path.join(directory,name);}
 try{
  await page.goto(pathToFileURL(process.env.HALITE_REAL_REVIEW_PATH).href);
  assert.match(await page.locator('#progress').innerText(),/150 · 0 saved/);assert.equal(await page.locator('#label').inputValue(),'');assert.equal(await page.locator('#reviewer').inputValue(),'Muhammad Umar');
  await page.screenshot({path:path.join(directory,'phase8-review-empty.png'),fullPage:true});
  await page.goto(pathToFileURL(process.env.HALITE_SYNTHETIC_REVIEW_PATH).href);
  await page.locator('#reviewer').fill('synthetic_browser_tester');await page.locator('#label').selectOption('supported');await page.locator('#rationale').fill('Synthetic test only, "quoted" rationale.');
  const draft=await download('#draft','synthetic-draft.json');
  await page.reload();await page.locator('#import').setInputFiles(draft);await page.waitForFunction(()=>document.getElementById('rationale').value.includes('quoted'));
  assert.equal(await page.locator('#label').inputValue(),'supported');
  await page.locator('#export').click();assert.match(await page.locator('#error').innerText(),/Complete every pair/);
  await page.locator('#save').click();await page.locator('#reviewer').fill('different_reviewer');await page.locator('#label').selectOption('unsupported');await page.locator('#rationale').fill('Synthetic test');await page.locator('#save').click();assert.match(await page.locator('#error').innerText(),/same reviewer/);await page.locator('#reviewer').fill('synthetic_browser_tester');
  for(let i=1;i<6;i++){await page.locator('#label').selectOption(i%2?'unsupported':'partly_supported');await page.locator('#rationale').fill('Synthetic browser test row '+i);await page.locator('#save').click();}
  await download('#export','synthetic-labels.csv');
  const wrong=JSON.parse(fs.readFileSync(draft));wrong.packet_sha256='foreign';const foreign=path.join(directory,'synthetic-foreign.json');fs.writeFileSync(foreign,JSON.stringify(wrong));await page.locator('#import').setInputFiles(foreign);await page.waitForFunction(()=>document.getElementById('error').textContent.includes('different packet'));
  assert.deepEqual(errors,[]);
  fs.writeFileSync(path.join(directory,'phase8-review-browser.json'),JSON.stringify({real_packet:{pairs:150,labels_entered:0,reviewer:'Muhammad Umar'},synthetic_packet:{pairs:6,draft_roundtrip:true,incomplete_csv_blocked:true,mixed_reviewers_blocked:true,foreign_draft_blocked:true,completed_csv_exported:true},page_errors:errors},null,2));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
