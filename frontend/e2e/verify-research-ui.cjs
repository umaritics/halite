// Hosted-only, disposable full-stack verification of the production-built page.
const { chromium } = require(process.env.HALITE_PLAYWRIGHT_MODULE || 'playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { createHash } = require('node:crypto');

async function verifySourceHighlights(page, context, base, token, directory, theme) {
  await page.setViewportSize({ width: 1280, height: 1000 });
  const ingest = await context.request.post(base + '/api/maintenance/ingest', {
    headers: { Authorization: 'Bearer ' + token }, data: { csv_path: '/app/tests/fixtures/grounding_highlight_smoke.csv' },
  });
  assert.equal(ingest.status(), 200);
  const ingested = await ingest.json();
  assert.equal(ingested.records_created + ingested.duplicates_skipped, 3);
  const pick = grounding => {
    const source = grounding.evidence.find(record => record.text.includes('😀'));
    assert.ok(source, 'Exact Unicode source retained');
    const sentence = grounding.sentences.find(item => item.candidates?.some(candidate => candidate.record_id === source.record_id && candidate.source_matches?.spans.length));
    assert.ok(sentence, 'Source has a sentence with recorded word positions');
    const candidate = sentence.candidates.find(item => item.record_id === source.record_id);
    return { source, sentence, annotation: candidate.source_matches };
  };
  const checkText = async (locator, selected) => {
    await locator.waitFor();
    assert.equal(await locator.textContent(), selected.source.text);
    assert.deepEqual(await locator.locator('mark').allTextContents(), selected.annotation.spans.map(span => selected.source.text.slice(span.start, span.end)));
  };
  await page.goto(base + '/app/investigations/quick');
  await page.getByRole('button', { name: /Select aircraft/ }).click();
  await page.getByRole('button', { name: /N-HGL-LIVE/ }).click();
  await page.getByLabel('Symptom', { exact: true }).fill('Hydraulic pump pressure loss');
  const quickResponse = page.waitForResponse(response => response.request().method() === 'POST' && new URL(response.url()).pathname === '/api/maintenance/diagnose');
  await page.getByRole('button', { name: 'Run diagnostic', exact: true }).click();
  const quick = await (await quickResponse).json();
  assert.equal(quick.llm_status, 'unavailable');
  const quickSource = pick(quick.grounding);
  await page.getByRole('region', { name: 'Checked explanation' }).getByRole('button', { name: quickSource.source.record_id, exact: true }).first().focus();
  const quickPanel = page.getByRole('region', { name: 'Cited report text' });
  await checkText(quickPanel.locator('[data-source-narrative]'), quickSource);
  await quickPanel.screenshot({ path: path.join(directory, `source-quick-${theme}.png`) });
  await page.goto(base + '/app/investigations');
  await page.getByLabel('Investigation title (optional)').fill('Synthetic saved word highlighting');
  const assetsResponse = await context.request.get(base + '/api/maintenance/assets', { headers: { Authorization: 'Bearer ' + token } });
  const asset = (await assetsResponse.json()).find(item => item.tail_number === 'N-HGL-LIVE');
  assert.ok(asset);
  await page.getByLabel('Aircraft', { exact: true }).selectOption(asset.id);
  await page.getByRole('button', { name: 'Create investigation', exact: true }).click();
  await page.getByRole('heading', { name: 'Synthetic saved word highlighting', exact: true }).waitFor();
  const sessionId = page.url().split('/app/investigations/')[1];
  await page.getByLabel('Symptom, observation or check result').fill('Hydraulic pump pressure loss');
  const turnResponse = page.waitForResponse(response => response.request().method() === 'POST' && new URL(response.url()).pathname === '/api/sessions/' + sessionId + '/turns');
  await page.getByRole('button', { name: 'Send observation', exact: true }).click();
  const turn = await (await turnResponse).json();
  const selected = pick(turn.grounding);
  const sentenceRegion = page.getByRole('region', { name: 'Checked explanation' }).last();
  await sentenceRegion.getByRole('button', { name: selected.source.record_id, exact: true }).first().hover();
  const saved = page.getByRole('region', { name: 'Saved evidence' });
  await checkText(saved.locator('details[open] [data-source-narrative]'), selected);
  await saved.screenshot({ path: path.join(directory, `source-session-${theme}-1280.png`) });
  const replayResponse = page.waitForResponse(response => response.request().method() === 'GET' && new URL(response.url()).pathname === '/api/sessions/' + sessionId);
  await page.reload();
  const replay = await (await replayResponse).json();
  assert.deepEqual(replay.turns[0].response.grounding, turn.grounding);
  await page.getByRole('region', { name: 'Checked explanation' }).last().getByRole('button', { name: selected.source.record_id, exact: true }).first().focus();
  await checkText(saved.locator('details[open] [data-source-narrative]'), selected);
  await page.setViewportSize({ width: 390, height: 844 });
  await saved.scrollIntoViewIfNeeded();
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
  await saved.screenshot({ path: path.join(directory, `source-session-${theme}-390.png`) });
  return { source_record_id: selected.source.record_id, matched_words: selected.annotation.spans.length, replay_exact: true, quick_and_session: true, unicode_offsets: true };
}

(async () => {
  const base = process.env.HALITE_UI_BASE_URL || 'http://127.0.0.1:5174';
  assert.ok(['127.0.0.1', 'localhost'].includes(new URL(base).hostname), 'Disposable loopback only');
  const directory = process.env.HALITE_UI_EVIDENCE_DIR || '/tmp/halite-research-ui-evidence';
  fs.mkdirSync(directory, { recursive: true });
  const browser = await chromium.launch({ headless: true, args: ['--no-sandbox'] });
  const errors = [];
  const proof = { themes: [], network: 'real authenticated endpoint; UI empty/error checks explicitly mocked', checks: [] };
  try {
    for (const theme of ['dark', 'light']) {
      const context = await browser.newContext({ viewport: { width: 1280, height: 1000 } });
      await context.addInitScript(value => localStorage.setItem('halite-theme', value), theme);
      const page = await context.newPage();
      page.on('pageerror', error => errors.push(error.message));
      await page.goto(base + '/login');
      await page.getByLabel(/work email/i).fill(process.env.HALITE_UI_ADMIN_EMAIL || 'admin@halite.local');
      await page.getByLabel(/^password$/i).fill(process.env.HALITE_UI_ADMIN_PASSWORD || 'HaliteDevAdmin2026');
      const loginResponse = page.waitForResponse(response => response.request().method() === 'POST' && new URL(response.url()).pathname === '/api/auth/login');
      await page.getByRole('button', { name: /^sign in$/i }).click();
      const login = await (await loginResponse).json();
      await page.getByRole('heading', { name: 'Maintenance workspace', exact: true }).waitFor();
      await page.getByRole('link', { name: 'Open investigations', exact: true }).click();
      const responsePromise = page.waitForResponse(r => new URL(r.url()).pathname === '/api/sessions/experiments');
      await page.getByRole('link', { name: 'How Halite decides', exact: true }).click();
      const response = await responsePromise;
      assert.equal(response.status(), 200);
      const data = await response.json();
      assert.equal(data.state, 'available');
      assert.equal(response.headers()['cache-control'], 'private, no-store');
      for (const entry of data.artifacts) {
        const raw = fs.readFileSync(path.resolve(__dirname, '../../backend/investigation/experiments/results', entry.path));
        assert.equal(createHash('sha256').update(raw).digest('hex'), entry.sha256);
      }
      await page.getByRole('heading', { name: 'How Halite decides', exact: true }).waitFor();
      const figures = page.locator('figure');
      await figures.nth(2).waitFor();
      assert.equal(await figures.count(), 3);
      await page.waitForFunction(() => document.querySelectorAll('svg.recharts-surface').length === 3);
      await page.waitForFunction(() => document.querySelectorAll('[class*="errorBar"]').length > 0);
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
      const budgetLabels = figures.first().locator('.recharts-xAxis-tick-labels .recharts-cartesian-axis-tick-value');
      await budgetLabels.first().waitFor();
      assert.deepEqual(await budgetLabels.allTextContents(), data.question_selection.summaries.all_attributes.all.policies.information_gain.map(row => String(row.after_questions)));
      await page.screenshot({ path: path.join(directory, `research-${theme}-1280.png`), fullPage: true });
      for (let index = 0; index < 3; index++) await figures.nth(index).screenshot({ path: path.join(directory, `research-${theme}-chart-${index}.png`) });
      await figures.first().getByText('View values and intervals', { exact: true }).click();
      const expected = data.question_selection.summaries.all_attributes.all.policies.information_gain[0].top1;
      assert.ok((await figures.first().locator('table').innerText()).includes(`${(expected * 100).toFixed(1)}%`));
      await page.getByLabel('Attribute control').selectOption('coded_fields_only');
      await page.getByLabel('Question metric').selectOption('entropy');
      await page.getByRole('heading', { name: 'Belief entropy (bits) after follow-up questions', exact: true }).waitFor();
      await page.getByLabel('Answered-case accuracy').selectOption('accuracy_top3');
      await page.reload();
      await page.getByRole('heading', { name: 'Top-1 accuracy after follow-up questions', exact: true }).waitFor();
      await page.setViewportSize({ width: 390, height: 844 });
      await figures.first().scrollIntoViewIfNeeded();
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
      const dimensions = await figures.first().boundingBox();
      assert.ok(dimensions.width > 250 && dimensions.x >= 0 && dimensions.x + dimensions.width <= 390);
      await page.screenshot({ path: path.join(directory, `research-${theme}-390.png`), fullPage: true });
      // Real data above; only these state-specific checks substitute endpoint responses.
      await page.route('**/api/sessions/experiments', route => route.fulfill({ status: 503, contentType: 'application/json', body: '{"detail":"synthetic outage"}' }));
      await page.reload();
      await page.getByRole('alert').waitFor();
      assert.equal(await page.locator('figure').count(), 0);
      await page.unroute('**/api/sessions/experiments');
      await page.route('**/api/sessions/experiments', route => route.fulfill({ contentType: 'application/json', body: '{"schema_version":"investigation-results-v1","state":"empty","artifacts":[]}' }));
      await page.getByRole('button', { name: 'Try again', exact: true }).click();
      await page.getByRole('heading', { name: 'No experiments published yet', exact: true }).waitFor();
      const sourceHighlights = await verifySourceHighlights(page, context, base, login.access_token, directory, theme);
      proof.themes.push({ sourceHighlights, theme, desktop: 1280, phone: 390, charts: 3, publication_sha256: data.publication_sha256, phoneFigure: dimensions });
      await context.close();
    }
    assert.deepEqual(errors, []);
    proof.checks = ['real JWT endpoint and artifact hashes', 'three rendered SVG charts with whiskers', 'saved value table parity', 'cohort/metric controls', 'production deep-link reload', 'dark/light 1280 and 390 geometry', 'explicitly mocked failure/retry/empty states', 'no browser exceptions', 'real quick/session source spans, Unicode offsets and exact saved replay'];
    fs.writeFileSync(path.join(directory, 'research-browser-proof.json'), JSON.stringify(proof, null, 2) + '\n');
    console.log(JSON.stringify(proof, null, 2));
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
