// Real built UI -> local API -> Neo4j; no mocked responses, no research labels.
const {chromium}=require(process.env.HALITE_PLAYWRIGHT_MODULE||'playwright');
const assert=require('node:assert/strict');const fs=require('node:fs');const path=require('node:path');
(async()=>{
 const directory=process.env.HALITE_UI_EVIDENCE_DIR||'/tmp/halite-grounding-live-browser';fs.mkdirSync(directory,{recursive:true});
 const browser=await chromium.launch({executablePath:'/usr/bin/google-chrome',headless:true,args:['--no-sandbox']});
 const page=await browser.newPage({viewport:{width:1280,height:1000}});const errors=[];page.on('pageerror',e=>errors.push(e.message));
 try{
  await page.goto('http://127.0.0.1:15173/login');await page.getByLabel(/work email/i).fill(process.env.HALITE_UI_ADMIN_EMAIL);await page.getByLabel(/^password$/i).fill(process.env.HALITE_UI_ADMIN_PASSWORD);await page.getByRole('button',{name:/^sign in$/i}).click();await page.getByRole('heading',{name:'Maintenance workspace',exact:true}).waitFor();
  await page.goto('http://127.0.0.1:15173/app/investigations/quick');await page.getByRole('button',{name:/Select aircraft/i}).click();await page.getByRole('button',{name:/N-Q-LIVE/}).click();await page.getByRole('textbox',{name:/symptom/i}).fill('Hydraulic pressure loss');
  const pending=page.waitForResponse(r=>r.request().method()==='POST'&&r.url().endsWith('/api/maintenance/diagnose'));await page.getByRole('button',{name:'Run diagnostic',exact:true}).click();const response=await pending;assert.equal(response.status(),200);const value=await response.json();assert.equal(value.llm_status,'unavailable');assert.equal(value.grounding.status,'thresholds_pending');assert.equal(value.grounding.checked_with,'lexical');assert.equal(value.grounding.unsupported_count,0,'All deterministic-summary citations are in its shown source list');
  const checked=page.getByRole('region',{name:'Checked explanation'});await checked.waitFor();const button=checked.getByRole('button').first();await button.focus();const id=await button.innerText();const source=value.grounding.evidence.find(r=>r.record_id===id);assert.ok(source?.text);const panel=page.getByRole('region',{name:'Cited report text'});await panel.waitFor();assert.ok((await panel.innerText()).includes(source.text));
  await page.screenshot({path:path.join(directory,'phase8-quick-grounding.png'),fullPage:true});assert.deepEqual(errors,[]);fs.writeFileSync(path.join(directory,'phase8-quick-grounding.json'),JSON.stringify({source:'Synthetic fixture, real local API/databases, fallback model',llm_status:value.llm_status,status:value.grounding.status,checked_with:value.grounding.checked_with,focused_citation:id,saved_narrative_exact:true,sentence_count:value.grounding.sentences.length,unsupported_count:value.grounding.unsupported_count,browser_errors:errors},null,2));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
