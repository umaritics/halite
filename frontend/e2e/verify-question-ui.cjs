// Built-app verification against disposable loopback databases; no network mocking.
const { chromium } = require(process.env.HALITE_PLAYWRIGHT_MODULE || 'playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { randomUUID, createHash } = require('node:crypto');

(async () => {
  const base = process.env.HALITE_UI_BASE_URL || 'http://127.0.0.1:15173';
  const apiBase = process.env.HALITE_API_BASE_URL || 'http://127.0.0.1:18000';
  for (const url of [base, apiBase]) assert.ok(['127.0.0.1', 'localhost', '::1'].includes(new URL(url).hostname), 'Disposable local servers only');
  const directory = process.env.HALITE_UI_EVIDENCE_DIR || '/tmp/halite-question-ui-evidence';
  fs.mkdirSync(directory, { recursive: true });
  const prefix = process.env.HALITE_UI_EVIDENCE_PREFIX || 'phase6';
  const suffix = randomUUID().slice(0, 8);
  const password = 'SyntheticQuestionBrowser2026';
  async function api(route, body, token) {
    const response = await fetch(apiBase + route, {
      method: body ? 'POST' : 'GET', headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: 'Bearer ' + token } : {}) },
      ...(body ? { body: JSON.stringify(body) } : {}),
    });
    if (!response.ok) throw new Error(`${route}: HTTP ${response.status}: ${await response.text()}`);
    return response.json();
  }
  const health = await api('/api/health');
  assert.equal(health.graph_mode, 'neo4j'); assert.equal(health.auth_db_mode, 'postgresql'); assert.equal(health.llm_mode, 'fallback');
  const admin = await api('/api/auth/login', { email: process.env.HALITE_UI_ADMIN_EMAIL, password: process.env.HALITE_UI_ADMIN_PASSWORD });
  const ingest = await api('/api/maintenance/ingest', { csv_path: process.env.HALITE_QUESTION_FIXTURE_PATH || path.resolve(__dirname, '../../backend/tests/fixtures/question_smoke.csv') }, admin.access_token);
  assert.equal(ingest.records_created + ingest.duplicates_skipped, 40);
  const readyHealth = await api('/api/health');
  assert.equal(readyHealth.maintenance_corpus_loaded, true);
  const invite = await api('/api/admin/invites', { email: `question-${suffix}@sessions.test`, full_name: 'Synthetic question owner', role: 'technician' }, admin.access_token);
  const account = await api('/api/auth/invites/accept', { token: invite.invite_token, password, full_name: 'Synthetic question owner' });
  const assets = await api('/api/maintenance/assets', null, admin.access_token);
  const asset = assets.find(item => item.tail_number === 'N-Q-LIVE');
  assert.ok(asset);
  const browser = await chromium.launch({ executablePath: process.env.HALITE_CHROME_EXECUTABLE || '/usr/bin/google-chrome', headless: true, args: ['--no-sandbox'] });
  const errors = [];
  let turnPosts = 0;
  const context = await browser.newContext({ viewport: { width: 1280, height: 1000 } });
  context.on('request', request => { if (request.method() === 'POST' && /\/api\/sessions\/[^/]+\/turns$/.test(new URL(request.url()).pathname)) turnPosts++; });
  const page = await context.newPage();
  page.on('pageerror', error => errors.push(error.message));
  const screenshot = async name => {
    await page.evaluate(() => document.fonts.ready);
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
    await page.screenshot({ path: path.join(directory, name.replace('phase6', prefix) + '.png'), fullPage: true });
  };
  try {
    await page.goto(base + '/login');
    await page.getByLabel(/work email/i).fill(`question-${suffix}@sessions.test`);
    await page.getByLabel(/^password$/i).fill(password);
    await page.getByRole('button', { name: /^sign in$/i }).click();
    await page.getByRole('heading', { name: 'Maintenance workspace', exact: true }).waitFor();
    await page.getByRole('link', { name: 'Open investigations', exact: true }).click();
    const title = 'Synthetic live question ' + suffix;
    await page.getByLabel('Investigation title (optional)').fill(title);
    await page.getByLabel('Aircraft', { exact: true }).selectOption(asset.id);
    await page.getByRole('button', { name: 'Create investigation', exact: true }).click();
    await page.getByRole('heading', { name: title, exact: true }).waitFor();
    const sessionId = page.url().split('/app/investigations/')[1];
    const route = '/api/sessions/' + sessionId;
    const turnResponse = () => page.waitForResponse(r => r.request().method() === 'POST' && r.url().endsWith(route + '/turns'));
    await page.getByLabel('Symptom, observation or check result').fill('Hydraulic pressure loss');
    let pending = turnResponse();
    await page.getByRole('button', { name: 'Send observation', exact: true }).click();
    let response = await pending;
    assert.equal(response.status(), 200);
    const initial = await response.json();
    assert.equal(initial.decision, 'ask'); assert.equal(initial.policy_status, 'experimental');
    assert.equal(initial.beliefs.label, 'relative support');
    await page.getByLabel('Your answer').waitFor();
    await page.getByText('Why this question:', { exact: false }).waitFor();
    const desktopSidebarWidth = await page.locator('aside').first().evaluate(el => el.getBoundingClientRect().width);
    assert.equal(desktopSidebarWidth, 256);
    await screenshot('phase6-question-before-answer');
    await page.setViewportSize({ width: 390, height: 844 });
    await page.getByLabel('Your answer').scrollIntoViewIfNeeded();
    const mobileActiveGeometry = await page.getByLabel('Your answer').evaluate(el => {
      const r = el.getBoundingClientRect();
      return { left: r.left, right: r.right, width: r.width, main_width: document.querySelector('main').getBoundingClientRect().width };
    });
    if (process.env.HALITE_UI_REQUIRE_MOBILE_LAYOUT === 'true') {
      assert.ok(mobileActiveGeometry.main_width >= 280, 'Phone workspace must have usable width');
      assert.ok(mobileActiveGeometry.width >= 200 && mobileActiveGeometry.left >= 64 && mobileActiveGeometry.right <= 390,
        'The active multiple-choice input must fit and remain usable on the phone');
    }
    await screenshot('phase6-question-mobile-active');
    await page.getByLabel('Your answer').selectOption(initial.question.options[0].value);
    pending = turnResponse();
    await page.getByRole('button', { name: 'Submit answer', exact: true }).click();
    response = await pending;
    assert.equal(response.status(), 200);
    const answered = await response.json();
    if (process.env.HALITE_UI_REQUIRE_GROUNDING === 'true') {
      for (const value of [initial, answered]) {
        assert.equal(value.grounding.status, 'thresholds_pending');
        assert.equal(value.grounding.checked_with, 'lexical');
        assert.ok(value.grounding.sentences.length > 0);
        assert.equal(value.grounding.parameters, null);
        assert.deepEqual(value.grounding.evidence, value.evidence);
        assert.ok(value.grounding.sentences.every(item => ['unrated', 'uncited', 'unsupported'].includes(item.level)));
      }
      await page.getByText('Sentence ratings await validation · lexical', { exact: true }).first().waitFor();
    }
    assert.equal(answered.llm_status, 'not_needed');
    assert.deepEqual(answered.belief_transition.prior, initial.beliefs);
    assert.notDeepEqual(answered.beliefs, initial.beliefs);
    await page.getByLabel('Your answer').waitFor();
    assert.equal(await page.getByLabel('Your answer').inputValue(), '');
    await page.setViewportSize({ width: 1280, height: 1000 });
    await page.locator('main > div').first().evaluate(el => { el.scrollTop = 0; });
    await screenshot('phase6-question-after-answer');
    // Refresh is read-only; exact server snapshot is the authority.
    const stored = await api(route, null, account.access_token);
    assert.deepEqual(stored.turns[0].response, initial); assert.deepEqual(stored.turns[1].response, answered);
    await page.reload();
    await page.getByLabel('Your answer').waitFor();
    assert.equal(turnPosts, 2);
    let latest = answered;
    const asked = new Set([initial.question.attribute]);
    while (latest.question) {
      assert.ok(!asked.has(latest.question.attribute));
      asked.add(latest.question.attribute);
      await page.getByLabel('Your answer').selectOption('not_sure');
      pending = turnResponse();
      await page.getByRole('button', { name: 'Submit answer', exact: true }).click();
      response = await pending;
      assert.equal(response.status(), 200);
      const next = await response.json();
      assert.deepEqual(next.beliefs, latest.beliefs);
      latest = next;
      assert.ok(turnPosts <= 4);
    }
    assert.equal(latest.decision, 'abstain');
    assert.equal(latest.policy_inputs.questions_asked, 3);
    await page.getByText('The history is insufficient for an answer.', { exact: false }).waitFor();
    await screenshot('phase6-question-budget-exhausted');
    await page.setViewportSize({ width: 390, height: 844 });
    const mobileMainWidth = await page.locator('main').evaluate(el => el.getBoundingClientRect().width);
    const mobileContentUsable = mobileMainWidth >= 280;
    if (process.env.HALITE_UI_REQUIRE_MOBILE_LAYOUT === 'true') assert.ok(mobileContentUsable, `Shared shell leaves only ${mobileMainWidth}px for content`);
    await page.locator('main > div').first().evaluate(el => { el.scrollTop = 0; });
    await screenshot('phase6-question-mobile');
    await page.reload();
    await page.getByLabel('Symptom, observation or check result').waitFor();
    assert.equal(turnPosts, 4);
    const saved = await api(route, null, account.access_token);
    assert.deepEqual(saved.turns.at(-1).response, latest);
    const mobileSidebar = page.locator('aside').first();
    for (const label of ['Home', 'Assets', 'Service Records', 'Investigations', 'Review Queue', 'Ingest', 'Knowledge Graph', 'Settings']) {
      assert.equal(await mobileSidebar.getByRole('link', { name: label, exact: true }).count(), 1);
    }
    await mobileSidebar.getByRole('link', { name: 'Investigations', exact: true }).focus();
    await page.keyboard.press('Enter');
    await page.waitForURL(/\/app\/investigations$/);
    await page.goto(base + '/app/investigations/' + sessionId);
    await page.getByLabel('Symptom, observation or check result').waitFor();
    assert.equal(turnPosts, 4, 'Keyboard navigation must not create inference turns');
    await page.getByRole('button', { name: 'Sign out', exact: true }).click();
    await page.getByLabel(/work email/i).waitFor();
    await page.goto(base + '/app/investigations/' + sessionId);
    await page.getByLabel(/work email/i).waitFor();
    assert.equal(await page.getByRole('heading', { name: title, exact: true }).count(), 0);
    assert.equal(errors.length, 0, errors.join('\n'));
    const sha = value => createHash('sha256').update(JSON.stringify(value)).digest('hex');
    fs.writeFileSync(path.join(directory, prefix + '-browser-proof.json'), JSON.stringify({
      source: 'Synthetic verification, not research accuracy or a selected operating point',
      health: readyHealth, session_id: sessionId, turn_posts: turnPosts, browser_errors: errors,
      initial: { decision: initial.decision, question: { attribute: initial.question.attribute, text: initial.question.text, reason: initial.question.reason, options: initial.question.options }, beliefs: initial.beliefs, response_sha256: sha(initial) },
      answer: { beliefs: answered.beliefs, llm_status: answered.llm_status, prior: answered.belief_transition.prior, response_sha256: sha(answered) },
      final: { decision: latest.decision, questions_asked: latest.policy_inputs.questions_asked, response_sha256: sha(latest) },
      sentence_grounding_verified: process.env.HALITE_UI_REQUIRE_GROUNDING === 'true',
      grounding: initial.grounding || null,
      exact_reload_replay: true, second_and_third_not_sure_preserve_beliefs: true,
      mobile_and_desktop_no_horizontal_overflow: true, desktop_sidebar_width_px: desktopSidebarWidth, phone_keyboard_navigation_and_logout_verified: true, mobile_active_question_geometry: mobileActiveGeometry, mobile_main_width_px: mobileMainWidth, mobile_content_usable: mobileContentUsable, shared_staging_accessed: false,
    }, null, 2) + '\n');
    console.log('LIVE_QUESTION_BROWSER_FLOW=PASS; EXACT_REPLAY=PASS; BUDGET=3; API_POSTS=4; MODEL_MODE=fallback');
  } finally { await context.close(); await browser.close(); }
})().catch(error => { console.error(error); process.exit(1); });
