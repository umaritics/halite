// Run against the feature preview or production shell and disposable loopback API.
const { chromium } = require(process.env.HALITE_PLAYWRIGHT_MODULE || 'playwright');
const fs = require('node:fs');
const path = require('node:path');
const { randomUUID } = require('node:crypto');
const assert = require('node:assert/strict');

(async () => {
  const base = process.env.HALITE_UI_BASE_URL || 'http://127.0.0.1:15173';
  const apiBase = process.env.HALITE_API_BASE_URL || 'http://127.0.0.1:18000';
  for (const url of [base, apiBase]) if (!['127.0.0.1', 'localhost', '::1'].includes(new URL(url).hostname)) throw new Error('Disposable loopback servers required');
  const directory = process.env.HALITE_UI_EVIDENCE_DIR || '/tmp/halite-investigation-ui-evidence';
  fs.mkdirSync(directory, { recursive: true });
  const productionShell = process.env.HALITE_UI_PRODUCTION_SHELL === 'true';
  const entry = route => base + (productionShell ? route : '/e2e/investigation-preview.html#' + route);
  const evidencePrefix = process.env.HALITE_UI_EVIDENCE_PREFIX || (productionShell ? 'phase3-integration' : 'phase3');
  const suffix = randomUUID().slice(0, 8);
  const password = 'BrowserTestPassword2026';
  async function api(route, body, token) {
    const response = await fetch(apiBase + route, {
      method: body ? 'POST' : 'GET', headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: 'Bearer ' + token } : {}) },
      ...(body ? { body: JSON.stringify(body) } : {}),
    });
    if (!response.ok) throw new Error(`Setup ${route}: HTTP ${response.status}: ${await response.text()}`);
    return response.json();
  }
  const health = await api('/api/health');
  assert.equal(health.graph_mode, 'neo4j'); assert.equal(health.auth_db_mode, 'postgresql'); assert.equal(health.llm_mode, 'fallback');
  const admin = await api('/api/auth/login', { email: process.env.HALITE_UI_ADMIN_EMAIL, password: process.env.HALITE_UI_ADMIN_PASSWORD });
  const accounts = {};
  for (const name of ['owner', 'other']) {
    const email = `browser-${name}-${suffix}@sessions.test`;
    const invite = await api('/api/admin/invites', { email, full_name: 'Browser ' + name, role: 'technician' }, admin.access_token);
    await api('/api/auth/invites/accept', { token: invite.invite_token, password, full_name: 'Browser ' + name });
    accounts[name] = email;
  }
  const assets = await api('/api/maintenance/assets', null, admin.access_token);
  const asset = assets.find(item => item.tail_number === 'N-CI-123');
  assert.ok(asset, 'Ingest the synthetic mid1_smoke.csv before this verification');
  const browser = await chromium.launch({ executablePath: process.env.HALITE_CHROME_EXECUTABLE, headless: true, args: ['--no-sandbox'] });
  const errors = [];
  let turnPosts = 0;
  const contexts = [];
  async function login(email) {
    const context = await browser.newContext({ viewport: { width: 1280, height: 900 } });
    contexts.push(context);
    context.on('request', request => { if (request.method() === 'POST' && /\/api\/sessions\/[^/]+\/turns$/.test(new URL(request.url()).pathname)) turnPosts += 1; });
    const page = await context.newPage();
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(entry('/login'));
    await page.evaluate(() => {
      localStorage.setItem('halite-diagnostic-active-workspace', 'unowned secret');
      localStorage.setItem('halite-diagnostic-copilot-sessions', 'unowned secret');
    });
    await page.getByLabel(/work email/i).fill(email);
    await page.getByLabel(/^password$/i).fill(password);
    await page.getByRole('button', { name: /^sign in$/i }).click();
    await page.getByRole('heading', { name: 'Maintenance workspace', exact: true }).waitFor();
    assert.equal(await page.evaluate(() => localStorage.getItem('halite-diagnostic-active-workspace')), null);
    assert.equal(await page.evaluate(() => localStorage.getItem('halite-diagnostic-copilot-sessions')), null);
    return { context, page };
  }
  async function screenshot(page, name) {
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth > innerWidth);
    assert.equal(overflow, false, 'Horizontal overflow at projector width');
    await page.screenshot({ path: path.join(directory, name.replace('phase3', evidencePrefix) + '.png'), fullPage: true });
  }
  try {
    const { page: first } = await login(accounts.owner);
    await first.getByRole('link', { name: 'Open investigations', exact: true }).click();
    const title = 'Browser investigation ' + suffix;
    await first.getByLabel('Investigation title (optional)').fill(title);
    await first.getByLabel('Aircraft', { exact: true }).selectOption(asset.id);
    await first.getByRole('button', { name: 'Create investigation', exact: true }).click();
    await first.getByRole('heading', { name: title, exact: true }).waitFor();
    const sessionId = decodeURIComponent(first.url().split('/app/investigations/')[1]);
    await first.getByLabel('Symptom, observation or check result').fill('Hydraulic pressure dropped during taxi');
    await first.getByRole('button', { name: 'Send observation', exact: true }).click();
    await first.getByText('Model unavailable · deterministic explanation', { exact: true }).waitFor();
    if (process.env.HALITE_UI_EXPECT_BELIEFS === 'true') {
      await first.getByRole('region', { name: 'Relative support', exact: true }).waitFor();
      assert.ok(await first.getByRole('meter').count() > 0);
    }
    await first.getByRole('button', { name: 'CI-SMOKE-001', exact: true }).click();
    await first.getByRole('region', { name: 'Saved evidence', exact: true }).getByText('Hydraulic pressure dropped during taxi', { exact: true }).waitFor();
    await screenshot(first, 'phase3-workspace-dark');
    if (productionShell) {
      // The existing Settings screen owns the application theme control.
      await first.getByRole('link', { name: 'Settings', exact: true }).click();
      await first.locator('button').filter({ has: first.locator('span.rounded-full') }).click();
      await first.goto(entry('/app/investigations/' + encodeURIComponent(sessionId)));
      await first.getByRole('heading', { name: title, exact: true }).waitFor();
    } else {
      await first.getByRole('button', { name: 'Light theme', exact: true }).click();
    }
    await first.waitForFunction(() => !document.documentElement.classList.contains('dark') && getComputedStyle(document.querySelector('#investigation-message')).backgroundColor === 'rgb(255, 255, 255)');
    await screenshot(first, 'phase3-workspace-light');
    await first.getByRole('button', { name: 'Close investigation', exact: true }).click();
    const dialog = first.getByRole('dialog');
    await dialog.getByLabel('Finding or outcome (required)').fill('Synthetic browser verification outcome.');
    await dialog.getByLabel('Part found (optional)').fill('HYDRAULIC PUMP');
    await dialog.getByRole('button', { name: 'Close with outcome', exact: true }).click();
    await first.getByText('Closed investigation — read only.', { exact: true }).waitFor();
    await screenshot(first, 'phase3-closed-outcome');
    const popupPromise = first.waitForEvent('popup');
    await first.getByRole('button', { name: 'Print investigation report', exact: true }).click();
    const popup = await popupPromise;
    await popup.getByRole('heading', { name: 'Recorded outcome', exact: true }).waitFor();
    assert.ok((await popup.textContent('body')).includes('CI-SMOKE-001'));
    await popup.close();
    const { context: secondContext, page: second } = await login(accounts.owner);
    await second.getByRole('link', { name: 'Open investigations', exact: true }).click();
    await second.getByRole('link', { name: title, exact: true }).click();
    await second.getByText('Closed investigation — read only.', { exact: true }).waitFor();
    await second.reload();
    await second.getByText('Synthetic browser verification outcome.', { exact: true }).waitFor();
    assert.equal(turnPosts, 1, 'Resume/reload must not create inference turns');
    await second.getByRole('link', { name: 'Investigations', exact: true }).click();
    await second.getByRole('link', { name: 'Quick diagnosis', exact: true }).click();
    await second.getByRole('button', { name: /Select aircraft/i }).click();
    await second.getByRole('button', { name: /N-CI-123/ }).click();
    await second.getByLabel('Symptom', { exact: true }).fill('hydraulic pressure loss');
    await second.getByRole('button', { name: 'Run diagnostic', exact: true }).click();
    await second.getByText('Model unavailable — the ranking and evidence remain available with a deterministic explanation.', { exact: true }).waitFor();
    await screenshot(second, 'phase3-quick-degraded');
    await secondContext.route('**/api/integrity/summary', route => route.fulfill({ status: 503, contentType: 'application/json', body: '{"detail":"Synthetic outage"}' }));
    await second.getByRole('link', { name: 'Home', exact: true }).click();
    await second.getByRole('heading', { name: 'Retrieval and ranking', exact: true }).waitFor();
    assert.equal(await second.getByRole('heading', { name: 'Record integrity', exact: true }).count(), 0);
    await screenshot(second, 'phase3-home-widget-outage');
    const { page: outsider } = await login(accounts.other);
    await outsider.goto(entry('/app/investigations/' + encodeURIComponent(sessionId)));
    await outsider.getByRole('alert').filter({ hasText: 'unavailable to your account' }).waitFor();
    assert.equal(await outsider.getByRole('heading', { name: title, exact: true }).count(), 0);
    assert.equal(errors.length, 0, errors.join('\n'));
    if (productionShell) {
      await second.goto(entry('/app/diagnostics'));
      await second.getByRole('heading', { name: 'Investigations', exact: true }).waitFor();
      assert.equal(new URL(second.url()).pathname, '/app/investigations');
      await second.evaluate(() => {
        localStorage.setItem('halite-diagnostic-active-workspace', 'unowned secret');
        localStorage.setItem('halite-diagnostic-copilot-sessions', 'unowned secret');
      });
      await second.getByRole('button', { name: 'Sign out', exact: true }).click();
      await second.getByRole('heading', { name: /sign in to workspace/i }).waitFor();
      assert.equal(await second.evaluate(() => localStorage.getItem('halite-diagnostic-active-workspace')), null);
      assert.equal(await second.evaluate(() => localStorage.getItem('halite-diagnostic-copilot-sessions')), null);
      await second.goto(entry('/app/investigations/' + encodeURIComponent(sessionId)));
      await second.getByRole('heading', { name: /sign in to workspace/i }).waitFor();
      await second.getByLabel(/work email/i).fill(accounts.other);
      await second.getByLabel(/^password$/i).fill(password);
      await second.getByRole('button', { name: /^sign in$/i }).click();
      await second.getByRole('alert').filter({ hasText: 'unavailable to your account' }).waitFor();
      assert.equal(await second.getByRole('heading', { name: title, exact: true }).count(), 0);
    }
    assert.equal(errors.length, 0, errors.join('\n'));
    const proof = { preview_harness: !productionShell, production_shell_integrated: productionShell,
      initial_health: { graph_mode: health.graph_mode, auth_db_mode: health.auth_db_mode, llm_mode: health.llm_mode },
      ...(productionShell ? { diagnostics_redirect: 'PASS', global_logout_legacy_cleanup: 'PASS', logout_protected_deep_link: 'PASS', next_account_isolation: 'PASS' } : {}),
      ...(process.env.HALITE_UI_EXPECT_BELIEFS === 'true' ? { relative_support_bars: 'PASS' } : {}),
      session_id: sessionId, create_and_degraded_turn: 'PASS', close_with_outcome: 'PASS', authenticated_print: 'PASS',
      second_browser_and_reload: 'PASS', other_technician_hidden: 'PASS', failed_widget_hidden: 'PASS',
      quick_diagnosis_model_off: 'PASS', turn_post_count: turnPosts, page_errors: errors, viewport: { width: 1280, height: 900 }, dark_and_light: 'PASS' };
    fs.writeFileSync(path.join(directory, evidencePrefix + '-browser-proof.json'), JSON.stringify(proof, null, 2) + '\n');
    process.stdout.write(productionShell ? 'INVESTIGATION_UI_PRODUCTION_SHELL=PASS\n' : 'INVESTIGATION_UI_PREVIEW=PASS\n');
  } catch (error) {
    let index = 0;
    for (const context of contexts) for (const page of context.pages()) {
      await page.screenshot({ path: path.join(directory, evidencePrefix + '-failure-' + index++ + '.png'), fullPage: true }).catch(() => {});
    }
    throw error;
  } finally {
    for (const context of contexts) await context.close();
    await browser.close();
  }
})().catch(error => { process.stderr.write(error.stack + '\n'); process.exitCode = 1; });
