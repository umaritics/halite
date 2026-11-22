// Explicitly authorized public-site acceptance. No inference or maintenance writes.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { createHash } = require('node:crypto');

const SITE = 'https://halite-mu.vercel.app';
const API = 'https://dev1.corp.curatech.pk/halite-api/api';
const API_ORIGIN = new URL(API).origin;
const API_PREFIX = new URL(API).pathname;
const AUTH_POSTS = new Set(['/auth/login', '/auth/refresh', '/auth/logout']);
const sha256 = value => createHash('sha256').update(value).digest('hex');
const proof = { schema: 'halite-public-read-acceptance-v1', state: 'running',
  started_at: new Date().toISOString(), frontend: SITE, backend: API,
  network: 'real public services; no fabricated responses', checks: [], requests: [],
  prohibited_requests: [], page_errors: [], screenshots: [] };
let stage = 'configuration';

async function main() {
  assert.equal(process.env.HALITE_UI_CONFIRMATION, 'VERIFY');
  assert.match(process.env.GITHUB_SHA || '', /^[a-f0-9]{40}$/);
  assert.ok(process.env.HALITE_UI_TEST_EMAIL && process.env.HALITE_UI_TEST_PASSWORD);
  const directory = process.env.HALITE_UI_EVIDENCE_DIR;
  assert.ok(directory && !fs.existsSync(directory), 'Fresh evidence directory required');
  fs.mkdirSync(directory, { recursive: true });
  const { chromium } = require(process.env.HALITE_PLAYWRIGHT_MODULE || 'playwright');
  let browser;
  let context;
  let signedIn = false;
  let page;
  const responseFor = (suffix, method = 'GET') => page.waitForResponse(response =>
    response.url().split('?')[0] === API + suffix && response.request().method() === method);
  const checkResponse = async promise => {
    const response = await promise;
    assert.equal(response.status(), 200);
    return response.json();
  };
  const capture = async name => {
    const filename = name + '.png';
    await page.screenshot({ path: path.join(directory, filename) });
    proof.screenshots.push({ file: filename, sha256: sha256(fs.readFileSync(path.join(directory, filename))), viewport: page.viewportSize() });
  };
  const geometry = async name => {
    const sizes = await page.evaluate(() => ({ width: innerWidth, scroll: document.documentElement.scrollWidth,
      main: document.querySelector('main')?.getBoundingClientRect().width }));
    assert.ok(sizes.scroll <= sizes.width, 'No document overflow');
    assert.ok(sizes.main >= 280, 'Usable main content width');
    proof.checks.push({ name, ...sizes });
  };
  try {
    browser = await chromium.launch({ headless: true, args: ['--no-sandbox'] });
    context = await browser.newContext({ viewport: { width: 1280, height: 1000 }, serviceWorkers: 'block' });
    context.setDefaultTimeout(45000);
    stage = 'health-before';
    const healthResponse = await context.request.get(API + '/health');
    assert.equal(healthResponse.status(), 200);
    const health = await healthResponse.json();
    assert.equal(health.git_sha, process.env.GITHUB_SHA);
    assert.equal(health.graph_mode, 'neo4j');
    assert.equal(health.llm_mode, 'live');
    assert.equal(health.maintenance_corpus_loaded, true);
    proof.health_before = health;
    await context.route('**/*', async route => {
      const request = route.request();
      const url = new URL(request.url());
      if (url.origin === API_ORIGIN && url.pathname.startsWith(API_PREFIX + '/')) {
        const suffix = url.pathname.slice(API_PREFIX.length);
        if (!['GET', 'HEAD', 'OPTIONS'].includes(request.method()) && !(request.method() === 'POST' && AUTH_POSTS.has(suffix))) {
          proof.prohibited_requests.push({ method: request.method(), path: suffix });
          await route.abort('blockedbyclient');
          return;
        }
      }
      await route.continue();
    });
    page = await context.newPage();
    page.on('pageerror', error => proof.page_errors.push({ type: error.name }));
    page.on('response', response => {
      const url = new URL(response.url());
      if (url.origin === API_ORIGIN && url.pathname.startsWith(API_PREFIX + '/')) {
        // Deliberately no headers, bodies, full URLs, exception messages or tokens.
        proof.requests.push({ method: response.request().method(), path: url.pathname.slice(API_PREFIX.length), status: response.status() });
      }
    });
    stage = 'protected-deep-link';
    await page.goto(SITE + '/app/investigations/experiments');
    await page.waitForURL(SITE + '/login');
    stage = 'login';
    await page.getByLabel(/work email/i).fill(process.env.HALITE_UI_TEST_EMAIL);
    await page.getByLabel(/^password$/i).fill(process.env.HALITE_UI_TEST_PASSWORD);
    const login = responseFor('/auth/login', 'POST');
    const research = responseFor('/sessions/experiments');
    await page.getByRole('button', { name: /^sign in$/i }).click();
    const session = await checkResponse(login);
    signedIn = true;
    assert.ok(session.access_token && session.refresh_token);
    assert.equal(session.user.email.toLowerCase(), process.env.HALITE_UI_TEST_EMAIL.toLowerCase());
    await page.waitForURL(SITE + '/app/investigations/experiments');
    stage = 'published-research';
    const publication = await checkResponse(research);
    assert.equal(publication.schema_version, 'investigation-results-v2');
    assert.equal(publication.state, 'available');
    for (const artifact of publication.artifacts) {
      const root = path.resolve(__dirname, '../../backend/investigation/experiments/results');
      const filename = path.resolve(root, artifact.path);
      assert.ok(filename.startsWith(root + path.sep));
      assert.equal(sha256(fs.readFileSync(filename)), artifact.sha256);
    }
    proof.publication_artifacts = publication.artifacts;
    await page.getByRole('heading', { name: 'How Halite decides', exact: true }).waitFor();
    assert.equal(await page.getByLabel('Evidence set').inputValue(), 'held_out');
    const selected = publication.held_out.stopping.find(row => row.cohort === 'all_attributes' && row.stratum === 'all' && row.availability === 'primary_all' && row.strategy === 'information_gain');
    assert.ok(selected);
    const caption = `${selected.chosen.n_pairs} cases, ${selected.chosen.n_originals} original reports. ${selected.chosen.n_answered} answers, ${selected.chosen.n_correct_top1} top-one matches, ${selected.chosen.n_pairs - selected.chosen.n_answered} abstentions.`;
    await page.getByText(caption, { exact: false }).waitFor();
    await page.locator('figure svg').first().waitFor();
    proof.checks.push({ name: 'research-source-and-render-parity', n_pairs: selected.chosen.n_pairs, n_answered: selected.chosen.n_answered, n_matches: selected.chosen.n_correct_top1 });
    await geometry('desktop-research');
    await capture('research-desktop-dark');
    for (const theme of ['light', 'dark']) {
      stage = 'refresh-research-' + theme;
      await page.evaluate(value => { localStorage.setItem('halite-theme', value); }, theme);
      const refresh = responseFor('/auth/refresh', 'POST');
      const reloadedResearch = responseFor('/sessions/experiments');
      await page.reload();
      await checkResponse(refresh);
      assert.deepEqual((await checkResponse(reloadedResearch)).artifacts, publication.artifacts);
      await page.getByRole('heading', { name: 'How Halite decides', exact: true }).waitFor();
      assert.equal(await page.evaluate(() => document.documentElement.classList.contains('dark')), theme === 'dark');
      await page.setViewportSize({ width: 390, height: 844 });
      await geometry('phone-research-' + theme);
      await capture('research-phone-' + theme);
      await page.setViewportSize({ width: 1280, height: 1000 });
    }
    stage = 'home';
    const homeReads = ['/retrieval/summary', '/integrity/summary', '/sessions/summary', '/sessions'].map(suffix => responseFor(suffix));
    await page.goto(SITE + '/app/home');
    const home = await Promise.all(homeReads.map(checkResponse));
    await page.getByRole('heading', { name: 'Maintenance workspace', exact: true }).waitFor();
    for (const widget of home.slice(0, 3)) {
      await page.getByRole('heading', { name: widget.title, exact: true }).waitFor();
    }
    assert.ok(Array.isArray(home[3].items));
    proof.checks.push({ name: 'home-real-summaries', widget_count: 3, recent_count: home[3].items.length });
    await capture('home-desktop');
    stage = 'history';
    const history = responseFor('/sessions');
    await page.getByRole('link', { name: 'Open investigations', exact: true }).click();
    const saved = await checkResponse(history);
    assert.ok(Array.isArray(saved.items));
    await page.getByRole('heading', { name: 'Investigations', exact: true }).waitFor();
    for (const item of saved.items) {
      await page.locator(`a[href="/app/investigations/${encodeURIComponent(item.id)}"]`).first().waitFor();
    }
    await page.setViewportSize({ width: 390, height: 844 });
    await geometry('phone-history');
    await capture('history-phone');
    proof.checks.push({ name: 'real-history-rendered', item_count: saved.items.length });
    const labelledCase = saved.items.find(item => item.title === 'Automated acceptance check - no maintenance finding'
      && item.status === 'closed' && item.user_id === session.user.id && item.turn_count > 0);
    if (process.env.HALITE_UI_REQUIRE_SAVED_CASE === 'true') assert.ok(labelledCase, 'Expected labelled own saved test case');
    if (labelledCase) {
      stage = 'saved-closed-workspace';
      const detailPath = '/sessions/' + labelledCase.id;
      const detail = responseFor(detailPath);
      await page.locator(`a[href="/app/investigations/${encodeURIComponent(labelledCase.id)}"]`).first().click();
      const snapshot = await checkResponse(detail);
      assert.equal(snapshot.status, 'closed');
      assert.ok(snapshot.turns.length && snapshot.turns[0].response.reply);
      await page.getByRole('heading', { name: labelledCase.title, exact: true }).waitFor();
      await page.getByText('Closed investigation — read only.', { exact: true }).waitFor();
      assert.equal(await page.getByLabel('Symptom, observation or check result', { exact: true }).count(), 0);
      await geometry('phone-closed-workspace');
      await capture('closed-workspace-phone');
      const refresh = responseFor('/auth/refresh', 'POST');
      const reloadedCase = responseFor(detailPath);
      await page.reload();
      await checkResponse(refresh);
      assert.deepEqual((await checkResponse(reloadedCase)).turns, snapshot.turns);
      stage = 'one-click-authenticated-print';
      const printResponse = responseFor(detailPath + '/report');
      const popupPromise = page.waitForEvent('popup');
      await page.getByRole('button', { name: 'Print investigation report', exact: true }).click();
      const popup = await popupPromise;
      assert.equal((await printResponse).status(), 200);
      await popup.getByRole('heading', { name: 'Recorded outcome', exact: true }).waitFor();
      assert.ok((await popup.textContent('body')).includes(snapshot.outcome_note));
      await popup.setViewportSize({ width: 794, height: 1123 });
      assert.equal(await popup.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
      await popup.pdf({ path: path.join(directory, 'closed-investigation-report.pdf'), format: 'A4', preferCSSPageSize: true, printBackground: true });
      await popup.close();
      proof.checks.push({ name: 'saved-closed-case-reload-and-one-click-print', session_id: labelledCase.id,
        turns: snapshot.turns.length, exact_replay: true, llm_status: snapshot.turns[0].response.llm_status,
        pdf_sha256: sha256(fs.readFileSync(path.join(directory, 'closed-investigation-report.pdf'))) });
      await page.getByRole('link', { name: 'Investigations', exact: true }).first().click();
    }
    stage = 'quick-entry';
    await page.getByRole('link', { name: 'Quick diagnosis', exact: true }).click();
    await page.getByLabel('Symptom', { exact: true }).waitFor();
    await page.getByRole('button', { name: 'Run diagnostic', exact: true }).waitFor();
    await geometry('phone-quick-entry');
    await capture('quick-entry-phone');
    stage = 'logout';
    const logout = responseFor('/auth/logout', 'POST');
    await page.getByRole('button', { name: 'Sign out', exact: true }).click();
    await checkResponse(logout);
    signedIn = false;
    await page.waitForURL(SITE + '/login');
    assert.equal(await page.evaluate(() => sessionStorage.getItem('halite.session.refresh.v1')), null);
    await page.goto(SITE + '/app/investigations/experiments');
    await page.waitForURL(SITE + '/login');
    assert.equal(await page.getByRole('heading', { name: 'How Halite decides', exact: true }).count(), 0);
    proof.checks.push({ name: 'logout-storage-and-protected-deep-link', passed: true });
    stage = 'health-after';
    const afterResponse = await context.request.get(API + '/health');
    assert.equal(afterResponse.status(), 200);
    const after = await afterResponse.json();
    assert.equal(after.git_sha, health.git_sha);
    assert.equal(after.maintenance_corpus_loaded, true);
    proof.health_after = after;
    assert.deepEqual(proof.prohibited_requests, []);
    assert.deepEqual(proof.page_errors, []);
    proof.state = 'passed';
    stage = 'complete';
  } catch (error) {
    proof.state = 'failed';
    proof.failure = { stage, type: error.name };
    process.exitCode = 1;
  } finally {
    if (signedIn && page) {
      try {
        // Use the app's own current refresh token, without exporting it to Node.
        await page.getByRole('button', { name: 'Sign out', exact: true }).click();
        await page.waitForURL(SITE + '/login');
        proof.cleanup_logout = 'completed';
      } catch { proof.cleanup_logout = 'unconfirmed'; }
    }
    if (browser) await browser.close();
    proof.finished_at = new Date().toISOString();
    fs.writeFileSync(path.join(directory, 'verification.json'), JSON.stringify(proof, null, 2) + '\n');
    console.log(JSON.stringify({ state: proof.state, stage, checks: proof.checks.length }));
  }
}

main().catch(error => {
  // Configuration failures must not print locator arguments or credentials.
  console.error(JSON.stringify({ state: 'failed', stage, type: error.name }));
  process.exitCode = 1;
});
