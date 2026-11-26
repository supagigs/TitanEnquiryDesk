export class ApiError extends Error {}

export async function call(method, args = {}, { post = false } = {}) {
  const url = `/api/method/${method}`
  const opts = { headers: { Accept: 'application/json', 'X-Frappe-CSRF-Token': window.csrf_token || '' }, credentials: 'same-origin' }
  let res
  if (post) {
    res = await fetch(url, { ...opts, method: 'POST', headers: { ...opts.headers, 'Content-Type': 'application/json' }, body: JSON.stringify(args) })
  } else {
    const q = new URLSearchParams(Object.entries(args).filter(([, v]) => v != null).map(([k, v]) => [k, typeof v === 'object' ? JSON.stringify(v) : v]))
    res = await fetch(`${url}?${q}`, opts)
  }
  const data = await res.json().catch(() => ({}))
  if (!res.ok) {
    let msg = res.status === 403 ? 'You do not have permission to do that.' : 'Something went wrong.'
    try { const m = JSON.parse(data._server_messages || '[]')[0]; if (m) msg = JSON.parse(m).message || msg } catch {}
    if (data.exception && !data._server_messages) msg = String(data.exception).split(':').slice(1).join(':').trim() || msg
    throw new ApiError(msg.replace(/<[^>]+>/g, ''))
  }
  return data.message
}

const D = 'titan_desk.desk.'
export const api = {
  boot: () => call('titan_desk.api.get_boot'),
  today: () => call(D + 'get_today'),
  inbox: (view, search) => call(D + 'get_inbox', { view, search }),
  conversation: (lead) => call(D + 'get_conversation', { lead }),
  sendReply: (a) => call(D + 'send_reply', a, { post: true }),
  updateSpec: (lead, product_line, values) => call(D + 'update_spec', { lead, product_line, values }, { post: true }),
  resolve: (lead) => call(D + 'resolve_escalation', { lead }, { post: true }),
  simulateIncoming: (lead, text) => call(D + 'simulate_incoming', { lead, text }, { post: true }),
  takeOver: (lead) => call('titan_desk.api.take_over', { lead }, { post: true }),
  toggleAi: (lead) => call('titan_desk.api.toggle_ai', { lead }, { post: true }),
  assign: (lead, user) => call('titan_desk.api.assign', { lead, user }, { post: true }),
  pipeline: () => call(D + 'get_pipeline'),
  moveStage: (lead, status) => call(D + 'move_stage', { lead, status }, { post: true }),
  calendar: (start, end) => call(D + 'get_calendar', { start, end }),
  bookCall: (lead, start, minutes = 30) => call(D + 'book_call', { lead, start, minutes }, { post: true }),
  cancelCall: (event) => call(D + 'cancel_call', { event }, { post: true }),
  approvals: (status) => call(D + 'get_approvals', { status }),
  decide: (name, decision, reason, text) => call(D + 'decide_approval', { name, decision, reason, text }, { post: true }),
  myPref: () => call(D + 'get_my_followup_preference'),
  setMyPref: (a) => call(D + 'set_my_followup_preference', a, { post: true }),
  whatsapp: () => call(D + 'get_whatsapp_status'),
  setup: () => call(D + 'get_setup_progress'),
  users: () => call('titan_desk.desk.get_desk_users'),
  seedDemo: () => call('titan_desk.demo.seed_demo', {}, { post: true }),
}

export function ago(dt) {
  if (!dt) return ''
  const d = new Date(String(dt).replace(' ', 'T'))
  const s = (Date.now() - d) / 1000
  if (s < 60) return 'now'
  if (s < 3600) return `${Math.floor(s / 60)} min`
  const today = new Date(); today.setHours(0, 0, 0, 0)
  if (d >= today) return d.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })
  if (s < 7 * 86400) return d.toLocaleDateString('en-IN', { weekday: 'short' })
  return d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })
}
export const time = (dt) => dt ? new Date(String(dt).replace(' ', 'T')).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' }) : ''
export const initials = (n) => (n || '?').split(/\s+/).slice(0, 2).map((w) => w[0]).join('').toUpperCase()
const AV = ['#25a35a', '#3a76f0', '#d9822b', '#8e5bd6', '#d14a6a', '#169c8f', '#b5651d', '#5b7fa6']
export const avatarColor = (s) => AV[[...(s || '')].reduce((a, c) => a + c.charCodeAt(0), 0) % AV.length]
