import { mkdir, writeFile } from 'node:fs/promises'
import { dirname, relative, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium } from '../../apps/web/node_modules/@playwright/test/index.mjs'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '../..')
const baseURL = process.env.FARMTACT_BASE_URL || 'http://127.0.0.1:8080'
const screenshotDir = resolve(root, process.env.FARMTACT_CONVERSATION_SCREENSHOT_DIR || 'apps/web/screenshots/conversations')
const reportPath = resolve(root, process.env.FARMTACT_CONVERSATION_REPORT || 'reports/conversations_browser.json')
const fixtureLabel = '[INTERCEPTED FIXTURE]'
const advisors = [
  { id: 'mei', name: 'Mei', role: 'Crop scientist' },
  { id: 'ravi', name: 'Ravi', role: 'Demand analyst' },
  { id: 'hana', name: 'Hana', role: 'Weather scout' },
  { id: 'ben', name: 'Ben', role: 'Resource analyst' },
  { id: 'asha', name: 'Asha', role: 'Planning chair' },
  { id: 'idris', name: 'Idris', role: 'Independent critic' },
]
const advisorById = Object.fromEntries(advisors.map(item => [item.id, item]))
const report = {
  started_at: new Date().toISOString(),
  base_url: baseURL,
  execution_policy: 'Browser-only deterministic intercepted API fixtures. No DeepSeek or other inference provider calls.',
  checks: [], failures: [], console_errors: [], expected_console_errors: [], page_errors: [], screenshots: [],
  intercepted: { conversation_requests: [], scenario_requests: [], provider_requests: [] },
}

function check(name, pass, detail) {
  report.checks.push({ name, pass, ...(detail === undefined ? {} : { detail }) })
  if (!pass) report.failures.push({ name, detail })
}

async function safely(name, action) {
  try { return await action() }
  catch (error) {
    check(name, false, error instanceof Error ? error.message : String(error))
    return undefined
  }
}

async function capture(page, filename) {
  const path = resolve(screenshotDir, filename)
  await page.screenshot({ path, animations: 'disabled', caret: 'hide' })
  report.screenshots.push(relative(root, path))
}

function json(route, body, status = 200) {
  return route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) })
}

function reducedDuration(value) {
  return value.split(',').every(part => {
    const duration = part.trim()
    const numeric = Number.parseFloat(duration)
    if (!Number.isFinite(numeric)) return false
    const seconds = duration.endsWith('ms') ? numeric / 1000 : duration.endsWith('s') ? numeric : Number.POSITIVE_INFINITY
    return seconds <= 0.00001
  })
}

function fixtureApi() {
  const conversations = new Map()
  const scenarioBodies = []
  const postBodies = []
  let conversationSerial = 0
  let messageSerial = 0
  let replayGets = 0
  let eventStreamGets = 0
  let reconnectId = null
  let reconnectReads = 0
  const delayedReads = new Map()

  const now = () => new Date().toISOString()
  const message = (conversation, speaker, content, fields = {}) => {
    const meta = advisorById[speaker]
    const item = {
      id: `fixture-message-${++messageSerial}`,
      conversation_id: conversation.id,
      speaker: speaker === 'user' ? 'user' : 'advisor',
      speaker_id: speaker === 'user' ? 'user' : speaker,
      speaker_name: speaker === 'user' ? 'You' : meta.name,
      content,
      created_at: now(),
      snapshot_ref: conversation.snapshot_ref,
      evidence_refs: [], tool_refs: [], highlight_refs: [], proposed_actions: [],
      validation_status: speaker === 'user' ? 'user_input' : 'references_verified',
      validation_scope: speaker === 'user' ? 'not_applicable' : 'reference_membership_and_supported_controls',
      interpretation_status: speaker === 'user' ? 'not_applicable' : 'unverified_advisor_interpretation',
      relationship: speaker === 'user' ? undefined : 'answer',
      ...fields,
    }
    conversation.messages.push(item)
    conversation.updated_at = now()
    return item
  }
  const publicConversation = conversation => JSON.parse(JSON.stringify(conversation))
  const createConversation = body => {
    const advisor = advisorById[body.advisor] || advisorById.asha
    const id = `fixture-conversation-${++conversationSerial}-${advisor.id}`
    const conversation = {
      id, title: `${advisor.name} · frozen fixture snapshot`, advisor_id: advisor.id, advisor_ids: [advisor.id],
      farm_id: 'demo-farm', scenario_id: body.snapshot_kind === 'scenario' ? body.snapshot_id : null,
      selected_bed_id: body.selected_bed_id || null, status: 'OPEN',
      snapshot_ref: { kind: body.snapshot_kind, id: body.snapshot_kind === 'scenario' ? body.snapshot_id : 'demo-farm:v1', hash: 'fixture-snapshot-hash', version: 1, frozen_at: now() },
      transcript_mode: 'recorded', execution_mode: 'fixture_intercept', inference_origin: 'stored_messages',
      last_request_id: null, last_request_status: null, created_at: now(), updated_at: now(), messages: [],
      tool_results: {
        'batch:batch-01.harvest_date': '2026-09-14',
        'batch:batch-01.expected_marketable_kg': 18.5,
        'comparison:balanced.deltas.margin_sgd': -42.5,
        'farm:resources.cash_sgd': 4000,
        'scenario:controls.delay_days': 3,
      },
      evidence_context: [{
        evidence_id: 'P01', title: 'Fixture crop timing reference',
        finding: 'This intercepted fixture demonstrates an expandable cited finding.',
        scope: 'Illustrative UI test data attached to the frozen fixture snapshot.',
        limit: 'This fixture does not establish conditions on a real farm.',
        source_url: 'https://www.nparks.gov.sg/publications-resources/articles/growing-five-leafy-vegetables',
        access_review_status: 'public_reference',
      }],
      validation_policy: {
        successful_status: 'references_verified',
        validation_scope: 'reference_membership_and_supported_controls',
        interpretation_status: 'unverified_advisor_interpretation',
      },
    }
    conversations.set(id, conversation)
    return conversation
  }
  const complete = conversation => {
    conversation.last_request_status = 'COMPLETED'
    conversation.last_request_id = `fixture-request-${messageSerial}`
  }
  const findMessage = (conversation, id) => conversation.messages.find(item => item.id === id)
  const answerTo = (conversation, body) => {
    const target = body.reply_to ? findMessage(conversation, body.reply_to) : null
    const responder = target?.speaker_id && advisorById[target.speaker_id] ? target.speaker_id : conversation.advisor_id
    const user = message(conversation, 'user', body.content, { reply_to: body.reply_to || null })
    if (body.content === 'fixture-budget-state') return { state: 'budget', user }
    if (body.content === 'fixture-service-state') return { state: 'service', user }
    if (body.content === 'fixture-interrupted-state') {
      conversation.last_request_status = 'INTERRUPTED'
      conversation.last_request_id = `fixture-request-${messageSerial}`
      return { state: 'interrupted', user }
    }
    const unsupported = body.content === 'fixture-unsupported-proposal'
    const response = message(conversation, responder,
      unsupported
        ? `${fixtureLabel} This interpretation has no accepted frozen reference, so its proposed change is blocked.`
        : body.reply_to
          ? `${fixtureLabel} I am answering the selected point while keeping this reply attached to it.`
          : `${fixtureLabel} The frozen schedule and comparison support inspecting timing and margin together.`, {
        reply_to: user.id,
        relationship: body.reply_to ? 'challenge' : 'answer',
        validation_status: unsupported ? 'unsupported' : 'references_verified',
        validation_scope: 'reference_membership_and_supported_controls',
        interpretation_status: 'unverified_advisor_interpretation',
        tool_refs: unsupported ? [] : ['batch:batch-01.harvest_date', 'comparison:balanced.deltas.margin_sgd'],
        evidence_refs: unsupported ? [] : ['P01'],
        highlight_refs: unsupported ? [] : ['bed:bed-01'],
        proposed_actions: [{ control: 'delay_days', target_id: 'batch-01', value: 3, unit: 'days', status: unsupported ? 'blocked_unsupported' : 'hypothesis_only' }],
      })
    complete(conversation)
    return { state: 'complete', user, response }
  }
  const invite = (conversation, body) => {
    const request = message(conversation, 'user', body.question, { reply_to: body.reply_to, relationship: 'challenge' })
    const invited = message(conversation, body.advisor, `${fixtureLabel} ${advisorById[body.advisor].name} disagrees with the selected point and requests a comparison.`, {
      reply_to: body.reply_to, relationship: 'disagreement', tool_refs: ['comparison:balanced.deltas.margin_sgd'], evidence_refs: ['P01'],
    })
    message(conversation, conversation.advisor_id, `${fixtureLabel} ${advisorById[conversation.advisor_id].name} answers that disagreement with the same frozen context.`, {
      reply_to: invited.id, relationship: 'challenge', tool_refs: ['batch:batch-01.expected_marketable_kg'], evidence_refs: ['P01'],
    })
    conversation.advisor_ids = [...new Set([...conversation.advisor_ids, body.advisor])]
    complete(conversation)
    return request
  }
  const council = (conversation, body) => {
    const user = message(conversation, 'user', body.question, { reply_to: body.reply_to || null })
    const sequence = [
      ['ravi', 'agreement'], ['mei', 'disagreement'], ['hana', 'challenge'], ['ben', 'answer'],
      ['asha', 'synthesis'], ['idris', 'challenge'], ['asha', 'synthesis'], ['idris', 'conclusion'],
    ]
    let replied = user.id
    for (const [speaker, relationship] of sequence) {
      const article = ['agreement', 'answer'].includes(relationship) ? 'an' : 'a'
      const turn = message(conversation, speaker, `${fixtureLabel} ${advisorById[speaker].name} records ${article} ${relationship} for the council transcript.`, {
        reply_to: replied, relationship, tool_refs: speaker === 'hana' ? [] : ['comparison:balanced.deltas.margin_sgd'],
        evidence_refs: speaker === 'hana' ? ['P01'] : [], request_mode: 'council',
        critic_conclusion: speaker === 'idris' && relationship === 'conclusion',
      })
      replied = turn.id
    }
    conversation.advisor_ids = advisors.map(item => item.id)
    complete(conversation)
  }
  const scenario = id => ({
    id, name: 'Conversation proposal fixture', controls: { batch_id: 'batch-01', delay_days: 3, yield_percent: 100, demand_crop_id: 'pak-choi', demand_percent: 100, labour_percent: 100, cash_percent: 100 },
    status: 'COMPLETED', simulation_status: 'FEASIBLE', input_hash: 'fixture-input-hash', baseline_hash: 'fixture-baseline-hash',
    source_conversation_id: scenarioBodies.at(-1)?.source_conversation_id || null, affected_bed_ids: ['bed-01'], affected_deliveries: [],
    policy_comparisons: ['Lean', 'Balanced', 'Resilient'].map(policy => ({
      policy, baseline_strategy_id: `${policy.toLowerCase()}-base`, scenario_strategy_id: `${policy.toLowerCase()}-scenario`, baseline_status: 'FEASIBLE', scenario_status: 'FEASIBLE',
      baseline_metrics: { fill_rate: .95, margin_sgd: 600, waste_kg: 4, shortfall_kg: 2, labour_hours: 31, cost_sgd: 200 },
      scenario_metrics: { fill_rate: .9, margin_sgd: 557.5, waste_kg: 5, shortfall_kg: 3, labour_hours: 32, cost_sgd: 210 },
      deltas: { fill_rate: -.05, margin_sgd: -42.5, waste_kg: 1, shortfall_kg: 1, labour_hours: 1, cost_sgd: 10 }, violations: [],
    })),
  })

  return {
    conversations, postBodies, scenarioBodies,
    createConversation,
    addMessage: message,
    delayConversationRead(id) {
      let markStarted, releaseRead
      const started = new Promise(resolve => { markStarted = resolve })
      const released = new Promise(resolve => { releaseRead = resolve })
      delayedReads.set(id, { markStarted, released })
      return {
        waitForStart: (timeout = 5_000) => Promise.race([started, new Promise((_, reject) => setTimeout(() => reject(new Error(`Timed out waiting for delayed read ${id}`)), timeout))]),
        release: () => releaseRead(),
      }
    },
    get replayGets() { return replayGets },
    get eventStreamGets() { return eventStreamGets },
    setReconnect(id) { reconnectId = id; reconnectReads = 0; const conversation = conversations.get(id); conversation.last_request_status = 'RUNNING'; message(conversation, 'user', 'Reconnect to this saved partial exchange.'); },
    async conversationRoute(route) {
      const request = route.request()
      const url = new URL(request.url())
      const method = request.method()
      const path = url.pathname
      let body = null
      if (method === 'POST') { try { body = request.postDataJSON() } catch { body = null } }
      report.intercepted.conversation_requests.push({ method, path, body, idempotency_key_present: Boolean(request.headers()['idempotency-key']) })
      if (path === '/api/v1/conversations' && method === 'GET') return json(route, { conversations: [...conversations.values()].map(publicConversation) })
      if (path === '/api/v1/conversations' && method === 'POST') {
        const conversation = createConversation(body || {})
        postBodies.push({ endpoint: 'create', body })
        return json(route, { id: conversation.id, status: conversation.status, reused: false }, 201)
      }
      const match = path.match(/^\/api\/v1\/conversations\/([^/]+)(?:\/(messages|invite|council|replay|events))?$/)
      if (!match || !conversations.has(match[1])) return json(route, { detail: 'Fixture conversation not found' }, 404)
      const conversation = conversations.get(match[1])
      const action = match[2]
      if (!action && method === 'GET') {
        const delayed = delayedReads.get(conversation.id)
        if (delayed) {
          delayed.markStarted()
          await delayed.released
          delayedReads.delete(conversation.id)
        }
        if (reconnectId === conversation.id) {
          reconnectReads += 1
          if (reconnectReads >= 2 && conversation.last_request_status === 'RUNNING') {
            message(conversation, conversation.advisor_id, `${fixtureLabel} The saved partial exchange resumed without duplicating the user message.`, {
              reply_to: conversation.messages.at(-1)?.id, relationship: 'answer', tool_refs: ['farm:resources.cash_sgd'], evidence_refs: ['P01'],
            })
            complete(conversation)
          }
        }
        return json(route, publicConversation(conversation))
      }
      if (action === 'replay' && method === 'GET') {
        replayGets += 1
        return json(route, { ...publicConversation(conversation), transcript_mode: 'replay', replay: true, inference_triggered: false, inference_origin: 'stored_messages' })
      }
      if (action === 'events' && method === 'GET') {
        eventStreamGets += 1
        return route.fulfill({ status: 200, contentType: 'text/event-stream', body: 'data: {"type":"fixture_event"}\n\n' })
      }
      if (method !== 'POST') return json(route, { detail: 'Method not allowed' }, 405)
      postBodies.push({ endpoint: action, body, conversation_id: conversation.id })
      if (action === 'messages') {
        if (body?.content === 'fixture-budget-state') return json(route, { detail: 'Daily inference budget exhausted for this fixture.' }, 429)
        if (body?.content === 'fixture-service-state') return json(route, { detail: 'Advisor service interrupted; the saved exchange can be retried.' }, 503)
        if (body?.content === 'fixture-delayed-switch') {
          const user = message(conversation, 'user', body.content)
          await new Promise(resolve => setTimeout(resolve, 1_200))
          message(conversation, conversation.advisor_id, `${fixtureLabel} Delayed Mei response stayed with Mei.`, {
            reply_to: user.id, relationship: 'answer', tool_refs: ['farm:resources.cash_sgd'], evidence_refs: ['P01'],
          })
          complete(conversation)
          return json(route, { id: conversation.last_request_id, conversation_id: conversation.id, status: 'COMPLETED', message_id: user.id }, 202)
        }
        const result = answerTo(conversation, body || {})
        return json(route, { id: conversation.last_request_id || `fixture-request-${messageSerial}`, conversation_id: conversation.id, status: conversation.last_request_status || 'INTERRUPTED', message_id: result.user.id }, 202)
      }
      if (action === 'invite') { invite(conversation, body); return json(route, { id: conversation.last_request_id, conversation_id: conversation.id, status: 'COMPLETED' }, 202) }
      if (action === 'council') { council(conversation, body); return json(route, { id: conversation.last_request_id, conversation_id: conversation.id, status: 'COMPLETED' }, 202) }
      return json(route, { detail: 'Unknown fixture action' }, 404)
    },
    async scenarioRoute(route) {
      const request = route.request()
      const url = new URL(request.url())
      const path = url.pathname
      const method = request.method()
      let body = null
      if (method === 'POST') { try { body = request.postDataJSON() } catch { body = null } }
      report.intercepted.scenario_requests.push({ method, path, body })
      if (path === '/api/v1/scenarios' && method === 'GET') return json(route, { scenarios: [] })
      if (path === '/api/v1/scenarios' && method === 'POST') {
        scenarioBodies.push(body)
        return json(route, { ...scenario('fixture-scenario'), controls: body.controls, name: body.name, source_conversation_id: body.source_conversation_id, status: 'DRAFT' }, 201)
      }
      if (path === '/api/v1/scenarios/compare' && method === 'GET') return json(route, { baseline: {}, scenarios: [scenario('fixture-scenario')] })
      const match = path.match(/^\/api\/v1\/scenarios\/([^/]+)(?:\/(run))?$/)
      if (match && method === 'POST' && match[2] === 'run') return json(route, scenario(match[1]), 202)
      if (match && method === 'GET') return json(route, scenario(match[1]))
      return json(route, { detail: 'Unknown fixture scenario route' }, 404)
    },
  }
}

await mkdir(screenshotDir, { recursive: true })
let browser
try {
  const fixtures = fixtureApi()
  browser = await chromium.launch({ headless: true })
  const context = await browser.newContext({ viewport: { width: 390, height: 844 }, reducedMotion: 'reduce' })
  await context.route('**://api.deepseek.com/**', route => {
    report.intercepted.provider_requests.push(route.request().url())
    return route.abort('blockedbyclient')
  })
  await context.route('**/api/v1/conversations**', route => fixtures.conversationRoute(route))
  await context.route('**/api/v1/scenarios**', route => fixtures.scenarioRoute(route))
  const page = await context.newPage()
  page.on('console', message => {
    if (message.type() !== 'error') return
    const detail = { text: message.text(), location: message.location() }
    const expectedFixtureError = /status of (429|503)/.test(detail.text) && detail.location.url.includes('/api/v1/conversations/') && detail.location.url.endsWith('/messages')
    if (expectedFixtureError) report.expected_console_errors.push(detail)
    else report.console_errors.push(detail)
  })
  page.on('pageerror', error => report.page_errors.push(error.message))
  await page.goto(baseURL, { waitUntil: 'networkidle' })

  const meiWorldLauncher = page.getByRole('button', { name: /^Talk to Mei,/ })
  await meiWorldLauncher.click()
  for (const advisor of advisors) {
    await safely(`${advisor.name} opens from advisor navigation`, async () => {
      let advisorDialog = page.getByRole('dialog', { name: `${advisor.name} · ${advisor.role}` })
      if (advisor.id !== 'mei') {
        const currentDialog = page.getByRole('dialog')
        await currentDialog.getByRole('button', { name: `Talk to ${advisor.name}`, exact: true }).click()
        advisorDialog = page.getByRole('dialog', { name: `${advisor.name} · ${advisor.role}` })
      }
      await advisorDialog.waitFor()
      check(`${advisor.name} opens from advisor navigation`, await advisorDialog.isVisible())
      check(`${advisor.name} shows expertise and current task`, (await advisorDialog.locator('.advisor-profile strong').textContent())?.trim().length > 10 && await advisorDialog.getByText(/Current context:/).isVisible())
    })
  }
  await page.getByRole('dialog', { name: 'Idris · Independent critic' }).getByRole('button', { name: 'Close' }).click()
  check('all six advisor conversation records use their role ids', new Set([...fixtures.conversations.values()].map(item => item.advisor_id)).size === 6, [...fixtures.conversations.values()].map(item => item.advisor_id))

  const currentMei = [...fixtures.conversations.values()].find(item => item.advisor_id === 'mei' && item.snapshot_ref.id === 'demo-farm:v1')
  const savedMei = fixtures.createConversation({ advisor: 'mei', snapshot_kind: 'farm', snapshot_id: 'demo-farm', selected_bed_id: 'bed-01' })
  savedMei.snapshot_ref.id = 'fixture-saved:v0'
  fixtures.addMessage(savedMei, 'mei', `${fixtureLabel} This is the deliberately selected older saved discussion.`)
  const currentRead = fixtures.delayConversationRead(currentMei.id)
  const savedRead = fixtures.delayConversationRead(savedMei.id)
  await page.getByRole('button', { name: /^Talk to Mei,/ }).click()
  const raceDialog = page.getByRole('dialog', { name: 'Mei · Crop scientist' })
  const savedSelect = raceDialog.getByLabel('Saved discussions')
  await savedSelect.waitFor()
  await currentRead.waitForStart()
  await savedSelect.selectOption(savedMei.id)
  await savedRead.waitForStart()
  const loadingLocks = {
    composer: await raceDialog.getByLabel('Message Mei').isDisabled(),
    send: await raceDialog.getByRole('button', { name: 'Send message' }).isDisabled(),
    invite: await raceDialog.getByRole('button', { name: 'Invite advisor' }).isDisabled(),
    council: await raceDialog.getByRole('button', { name: 'Convene council' }).isDisabled(),
    suggestions: await raceDialog.locator('.prompt-row button').evaluateAll(buttons => buttons.every(button => button.disabled)),
  }
  check('saved-discussion loading disables every inference action', Object.values(loadingLocks).every(Boolean), loadingLocks)
  savedRead.release()
  await raceDialog.getByText(/Saved frozen discussion · fixture-saved:v0/).waitFor()
  currentRead.release()
  await page.waitForTimeout(250)
  check('delayed current-snapshot read cannot overwrite a selected saved discussion', await savedSelect.inputValue() === savedMei.id && await raceDialog.getByText(`${fixtureLabel} This is the deliberately selected older saved discussion.`).isVisible(), { selected: await savedSelect.inputValue(), expected: savedMei.id })
  await raceDialog.getByRole('button', { name: 'Close' }).click()

  await page.getByRole('button', { name: /^Talk to Mei,/ }).click()
  const delayedMeiDialog = page.getByRole('dialog', { name: 'Mei · Crop scientist' })
  await delayedMeiDialog.getByLabel('Message Mei').fill('fixture-delayed-switch')
  await delayedMeiDialog.getByRole('button', { name: 'Send message' }).click()
  await delayedMeiDialog.getByRole('button', { name: 'Talk to Ravi', exact: true }).click()
  const switchedRaviDialog = page.getByRole('dialog', { name: 'Ravi · Demand analyst' })
  await switchedRaviDialog.waitFor()
  await page.waitForTimeout(1_500)
  check('delayed response cannot overwrite a newly selected advisor', await switchedRaviDialog.getByText(`${fixtureLabel} Delayed Mei response stayed with Mei.`).count() === 0 && await switchedRaviDialog.getByLabel('Message Ravi').isVisible())
  await switchedRaviDialog.getByRole('button', { name: 'Talk to Mei', exact: true }).click()
  await page.getByRole('dialog', { name: 'Mei · Crop scientist' }).getByText(`${fixtureLabel} Delayed Mei response stayed with Mei.`).waitFor({ timeout: 8_000 })
  check('delayed response remains in its originating saved conversation', [...fixtures.conversations.values()].find(item => item.advisor_id === 'mei')?.messages.some(item => item.content.includes('Delayed Mei response stayed with Mei.')) === true)
  await page.getByRole('dialog', { name: 'Mei · Crop scientist' }).getByRole('button', { name: 'Close' }).click()

  const meiLauncher = page.getByRole('button', { name: /^Talk to Mei,/ })
  await meiLauncher.focus(); await meiLauncher.click()
  const dialog = page.getByRole('dialog', { name: 'Mei · Crop scientist' })
  await dialog.waitFor()
  const close = dialog.getByRole('button', { name: 'Close' })
  check('conversation modal focuses its close control', await close.evaluate(node => node === document.activeElement))
  await page.keyboard.press('Shift+Tab')
  check('conversation modal traps reverse-tab focus', await dialog.evaluate(node => node.contains(document.activeElement)), await page.evaluate(() => document.activeElement?.getAttribute('aria-label') || document.activeElement?.textContent?.trim()))
  await close.focus()

  const composer = dialog.getByLabel('Message Mei')
  const streamsBeforeFirstMessage = fixtures.eventStreamGets
  await composer.fill('Why is the selected bed delayed?')
  await dialog.getByRole('button', { name: 'Send message' }).click()
  const firstReply = dialog.locator('.message-card--advisor').filter({ hasText: `${fixtureLabel} The frozen schedule` })
  await firstReply.waitFor({ timeout: 8_000 })
  check('typed question produces an attached advisor response', await firstReply.isVisible())
  check('typed response subscribes to stored conversation events', fixtures.eventStreamGets > streamsBeforeFirstMessage, { before: streamsBeforeFirstMessage, after: fixtures.eventStreamGets })
  check('verified references are labelled without claiming semantic validation', await firstReply.getByText('References checked · advisor interpretation').isVisible() && await firstReply.getByText(/interpretation remains unverified/i).isVisible())
  check('frozen fact cards render exact referenced values', await firstReply.getByText('Facts from this frozen snapshot').isVisible() && await firstReply.getByText('14 Sept 2026').isVisible() && await firstReply.getByText(/-\$42\.50/).isVisible())
  check('supported control is labelled as a proposed experiment', await firstReply.getByText('Proposed experiment', { exact: true }).isVisible())
  const evidence = firstReply.getByText('P01 · Fixture crop timing reference')
  await evidence.click()
  check('evidence expands with scope, limit, and source link', await firstReply.getByText(/Illustrative UI test data/).isVisible() && await firstReply.getByText(/does not establish conditions/).isVisible() && await firstReply.getByRole('link', { name: 'Read source ↗' }).isVisible())

  await firstReply.getByRole('button', { name: 'Show referenced plots' }).click()
  await dialog.waitFor({ state: 'hidden' })
  check('verified message highlights its referenced farm plot', await page.locator('.world-bed.is-affected').filter({ has: page.getByLabel('Referenced by advisor') }).count() === 1)
  await page.getByRole('button', { name: /^Talk to Mei,/ }).click()
  await dialog.waitFor()

  const firstReplyId = [...fixtures.conversations.values()].find(item => item.advisor_id === 'mei').messages.find(item => item.content.includes('frozen schedule')).id
  await firstReply.getByRole('button', { name: 'Reply to this point' }).click()
  check('reply selection is visibly announced', await dialog.getByRole('button', { name: /Replying to a specific message/ }).isVisible())
  await composer.fill('Which part of that point would you challenge?')
  await dialog.getByRole('button', { name: 'Send message' }).click()
  await dialog.getByText(`${fixtureLabel} I am answering the selected point while keeping this reply attached to it.`).waitFor({ timeout: 8_000 })
  const challengePost = fixtures.postBodies.filter(item => item.endpoint === 'messages').at(-1)
  check('typed challenge sends the selected reply reference', challengePost?.body?.reply_to === firstReplyId, challengePost?.body)
  check('reply relationship names and quotes the selected point', await dialog.getByText(/replies to Mei: “\[INTERCEPTED FIXTURE\] The frozen schedule/).isVisible())

  await firstReply.getByRole('button', { name: 'Reply to this point' }).click()
  await dialog.locator('.conversation-actions select').selectOption('idris')
  await dialog.getByRole('button', { name: 'Invite advisor' }).click()
  await dialog.getByText(`${fixtureLabel} Idris disagrees with the selected point and requests a comparison.`).waitFor({ timeout: 8_000 })
  const invitePost = fixtures.postBodies.filter(item => item.endpoint === 'invite').at(-1)
  check('invitation targets the specifically selected point', invitePost?.body?.reply_to === firstReplyId, { expected: firstReplyId, actual: invitePost?.body?.reply_to, body: invitePost?.body })
  check('invited advisor and original advisor exchange specific linked replies', await dialog.locator('.message-card--advisor > p').filter({ hasText: `${fixtureLabel} Idris disagrees` }).isVisible() && await dialog.locator('.message-card--advisor > p').filter({ hasText: `${fixtureLabel} Mei answers that disagreement` }).isVisible() && await dialog.getByText(/replies to Idris/).first().isVisible())
  check('a two-advisor invitation is not mislabeled as a council', await dialog.getByLabel('Council speakers').count() === 0)

  await composer.fill('Compare the trade-offs and record the critic conclusion.')
  await dialog.getByRole('button', { name: 'Convene council' }).click()
  await dialog.getByText(`${fixtureLabel} Idris records a conclusion for the council transcript.`).waitFor({ timeout: 8_000 })
  const councilTurns = [...fixtures.conversations.values()].find(item => item.advisor_id === 'mei').messages.filter(item => item.request_mode === 'council')
  const renderedCouncilTurns = await dialog.locator('.message-card--advisor').filter({ hasText: 'for the council transcript.' }).count()
  check('council renders eight bounded advisor turns', councilTurns.length === 8 && renderedCouncilTurns === 8, { recorded: councilTurns.length, rendered: renderedCouncilTurns })
  check('council transcript exposes agreements, disagreements, and critic conclusion', await dialog.getByText(/records an agreement/).count() > 0 && await dialog.getByText(/records a disagreement/).count() > 0 && await dialog.getByText(/Idris records a conclusion/).count() > 0)
  check('critic conclusion is explicitly identified', await dialog.getByText('Critic’s conclusion', { exact: true }).isVisible() && councilTurns.at(-1)?.critic_conclusion === true)
  check('council discussion is staged with all six speakers', await dialog.getByLabel('Council speakers').isVisible() && await dialog.getByLabel('Council speakers').locator('span').count() === 6)

  await composer.fill('fixture-unsupported-proposal')
  await dialog.getByRole('button', { name: 'Send message' }).click()
  const unsupported = dialog.locator('.message-card--advisor').filter({ hasText: 'has no accepted frozen reference' })
  await unsupported.waitFor({ timeout: 8_000 })
  check('unsupported advice is visibly flagged', await unsupported.getByText('Unsupported suggestion · blocked', { exact: true }).isVisible() && await unsupported.getByText('Unsupported advice cannot authorize a change.').isVisible())
  check('unsupported proposed controls cannot open an experiment', await unsupported.getByRole('button', { name: /delay days = 3 days/i }).isDisabled())

  await firstReply.getByRole('button', { name: /delay days = 3 days/i }).click()
  const lab = page.getByRole('dialog', { name: 'Scenario lab' })
  await lab.waitFor()
  const delayControl = lab.getByRole('slider', { name: 'Harvest delay' })
  check('supported proposal prefills its exact bounded control', await delayControl.inputValue() === '3', await delayControl.inputValue())
  await lab.getByRole('button', { name: 'Run experiment' }).click()
  await lab.getByText('Inspect the trade-offs').waitFor({ timeout: 8_000 })
  const scenarioBody = fixtures.scenarioBodies.at(-1)
  const meiConversation = [...fixtures.conversations.values()].find(item => item.advisor_id === 'mei')
  check('proposal branch keeps source conversation and frozen snapshot association', scenarioBody?.source_conversation_id === meiConversation.id && scenarioBody?.controls?.delay_days === 3, scenarioBody)
  await lab.getByRole('button', { name: 'Close' }).click()
  await page.getByRole('button', { name: /^Talk to Mei,/ }).click()
  await dialog.waitFor()

  await composer.fill('fixture-budget-state'); await dialog.getByRole('button', { name: 'Send message' }).click()
  await dialog.getByRole('alert').waitFor()
  check('budget exhaustion is shown as a usable inline error', await dialog.getByRole('alert').getByText(/Daily inference budget exhausted/).isVisible())
  await composer.fill('fixture-service-state'); await dialog.getByRole('button', { name: 'Send message' }).click()
  await dialog.getByRole('alert').getByText(/Advisor service interrupted/).waitFor()
  check('provider error explains that the saved exchange can be retried', await dialog.getByRole('alert').getByText(/saved exchange can be retried/).isVisible())
  await composer.fill('fixture-interrupted-state'); await dialog.getByRole('button', { name: 'Send message' }).click()
  await page.waitForTimeout(1_100)
  check('interrupted request state is visible in the conversation', await dialog.getByText(/Response interrupted|Request interrupted|Saved partial/i).isVisible())

  const streamsBeforeReconnect = fixtures.eventStreamGets
  fixtures.setReconnect(meiConversation.id)
  await page.reload({ waitUntil: 'networkidle' })
  await page.getByRole('button', { name: /^Talk to Mei,/ }).click()
  const reconnected = page.getByRole('dialog', { name: 'Mei · Crop scientist' })
  await reconnected.getByText(`${fixtureLabel} The saved partial exchange resumed without duplicating the user message.`).waitFor({ timeout: 8_000 })
  check('reload reconnects to the pending stored exchange', await reconnected.getByText(/resumed without duplicating/).isVisible())
  check('reconnect subscribes to stored conversation events', fixtures.eventStreamGets > streamsBeforeReconnect, { before: streamsBeforeReconnect, after: fixtures.eventStreamGets })
  const reconnectUsers = meiConversation.messages.filter(item => item.content === 'Reconnect to this saved partial exchange.').length
  check('reconnect does not duplicate the saved user turn', reconnectUsers === 1, reconnectUsers)

  const postsBeforeReplay = report.intercepted.conversation_requests.filter(item => item.method === 'POST').length
  const messagesBeforeReplay = meiConversation.messages.length
  await reconnected.getByRole('button', { name: 'Replay' }).click()
  await reconnected.getByText(/Recorded replay · opening and replaying use no new inference/).waitFor()
  const postsAfterReplay = report.intercepted.conversation_requests.filter(item => item.method === 'POST').length
  check('replay reads the stored transcript without POST or new messages', postsAfterReplay === postsBeforeReplay && meiConversation.messages.length === messagesBeforeReplay && fixtures.replayGets === 1, { postsBeforeReplay, postsAfterReplay, messagesBeforeReplay, messagesAfterReplay: meiConversation.messages.length, replayGets: fixtures.replayGets })

  const reducedDurations = await reconnected.locator('.game-panel,.thinking-dots i,.message-card').evaluateAll(nodes => nodes.map(node => ({ className: node.className, animationDuration: getComputedStyle(node).animationDuration, transitionDuration: getComputedStyle(node).transitionDuration })))
  check('conversation honors reduced motion', reducedDurations.every(item => reducedDuration(item.animationDuration) && reducedDuration(item.transitionDuration)), reducedDurations)
  await capture(page, 'conversation-replay-390.png')

  await page.setViewportSize({ width: 360, height: 844 })
  const shortcutLayout = await reconnected.locator('.advisor-switcher').evaluate(node => {
    const box = node.getBoundingClientRect()
    const buttons = [...node.querySelectorAll('button')]
    return {
      height: box.height,
      overflow_x: node.scrollWidth > node.clientWidth,
      buttons: buttons.map(button => {
        const buttonBox = button.getBoundingClientRect()
        const nameBox = button.querySelector('span')?.getBoundingClientRect()
        return { height: buttonBox.height, name: button.textContent?.trim(), name_inside_row: Boolean(nameBox && nameBox.top >= box.top && nameBox.bottom <= box.bottom) }
      }),
    }
  })
  check('all six advisor shortcuts remain usable in a nonshrinking mobile row', shortcutLayout.height >= 58 && shortcutLayout.overflow_x && shortcutLayout.buttons.length === 6 && shortcutLayout.buttons.every(button => button.height >= 58 && button.name_inside_row), shortcutLayout)
  await reconnected.locator('.game-panel__body').evaluate(node => { node.scrollTop = node.scrollHeight })
  const mobileConversationLayout = await reconnected.evaluate(node => {
    const transcript = node.querySelector('.conversation-transcript')
    const composer = node.querySelector('.conversation-composer')
    const input = node.querySelector('.conversation-composer input')
    const actions = [...node.querySelectorAll('.conversation-actions > *')]
    const insideViewport = element => { const box = element.getBoundingClientRect(); return box.left >= 0 && box.right <= innerWidth && box.top >= 0 && box.bottom <= innerHeight }
    return {
      body_overflow: document.body.scrollWidth - innerWidth,
      transcript_height: transcript?.getBoundingClientRect().height || 0,
      composer_visible: Boolean(composer && insideViewport(composer)),
      composer_font_size: input ? Number.parseFloat(getComputedStyle(input).fontSize) : 0,
      action_count: actions.length,
      action_heights: actions.map(action => action.getBoundingClientRect().height),
      actions_visible: actions.every(insideViewport),
    }
  })
  check('360px preserves the transcript, readable composer, and bottom actions', mobileConversationLayout.body_overflow <= 1 && mobileConversationLayout.transcript_height >= 210 && mobileConversationLayout.composer_visible && mobileConversationLayout.composer_font_size >= 12 && mobileConversationLayout.action_count === 4 && mobileConversationLayout.action_heights.every(height => height >= 44) && mobileConversationLayout.actions_visible, mobileConversationLayout)
  await capture(page, 'conversation-replay-360.png')

  const launcher = page.getByRole('button', { name: /^Talk to Mei,/ })
  await page.keyboard.press('Escape')
  check('Escape closes the modal and restores launcher focus', await launcher.evaluate(node => node === document.activeElement))
  check('all intercepted conversation mutations carried idempotency keys', report.intercepted.conversation_requests.filter(item => item.method === 'POST').every(item => item.idempotency_key_present), report.intercepted.conversation_requests.filter(item => item.method === 'POST' && !item.idempotency_key_present))
  check('no browser request reached an inference provider', report.intercepted.provider_requests.length === 0, report.intercepted.provider_requests)
  const advisorFixtureMessages = meiConversation.messages.filter(item => item.speaker === 'advisor')
  check('fixture responses are visibly labelled and distinguishable from DeepSeek', advisorFixtureMessages.length > 0 && advisorFixtureMessages.every(item => item.content.startsWith(fixtureLabel)), advisorFixtureMessages.map(item => item.content))
  check('no browser console errors', report.console_errors.length === 0, report.console_errors)
  check('no uncaught page errors', report.page_errors.length === 0, report.page_errors)
  await context.close()
} catch (error) {
  report.failures.push({ name: 'suite execution', detail: error instanceof Error ? error.stack || error.message : String(error) })
} finally {
  if (browser) await browser.close()
  report.completed_at = new Date().toISOString()
  report.status = report.failures.length ? 'FAIL' : 'PASS'
  await mkdir(dirname(reportPath), { recursive: true })
  await writeFile(reportPath, `${JSON.stringify(report, null, 2)}\n`)
}

if (report.failures.length) {
  process.stderr.write(`${JSON.stringify(report.failures, null, 2)}\n`)
  process.exitCode = 1
}
