import { chromium } from '../../apps/web/node_modules/@playwright/test/index.mjs'

const base = (process.env.FARMTACT_BASE_URL || 'http://127.0.0.1:8080').replace(/\/$/, '')
const fixture = ['v2','v11','v9','v10'].map((id, index) => ({ id, title: `Edition ${id}`, published_at: `2026-09-${String(index + 1).padStart(2,'0')}T00:00:00Z`, summary: id, changes: [], source_commit: id, source_url: '#', compare_url: '#', image_digest: id, review_url: `/${id}/review`, play_url: `/${id}/`, status: 'published' }))
let browser
try {
  browser = await chromium.launch({ headless: true })
  const page = await browser.newPage()
  await page.route('**/api/releases', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ latest: 'v11', editions: fixture }) }))
  await page.goto(base, { waitUntil: 'domcontentloaded' })
  const cards = await page.locator('.edition-card .button--forest').allTextContents()
  if (cards.map(value => value.match(/V\d+/)?.[0]).join(',') !== 'V11,V10,V9,V2') throw new Error(`chooser is not numeric newest-first: ${cards}`)
  if (await page.locator('.edition-card').first().getByText('Latest edition', { exact: true }).count() !== 1) throw new Error('latest badge is not retained on first card')
  await page.goto(`${base}/v11/`, { waitUntil: 'domcontentloaded' })
  const options = await page.getByRole('combobox', { name: 'Choose FarmTact edition' }).first().locator('option').evaluateAll(nodes => nodes.map(node => node.value))
  if (options.join(',') !== 'v11,v10,v9,v2') throw new Error(`switcher is not numeric newest-first: ${options}`)
  console.log(JSON.stringify({ status: 'PASS', chooser: cards, switcher: options }))
} finally { if (browser) await browser.close() }
