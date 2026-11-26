<template>
  <h2 class="hello" style="margin-top:0">Inbox</h2>
  <p class="lede">WhatsApp chats and emails for each lead, with the requirement sheet beside them.</p>
  <div class="inbox">
    <div class="card lst">
      <div class="whd"><b>Chats</b></div>
      <div class="wsrch"><input v-model="q" placeholder="Search name, company or number" aria-label="Search chats" @input="debounced" /></div>
      <div class="tabs"><button v-for="v in views" :key="v" :class="{ on: v === view }" @click="view = v; loadList()">{{ v }}</button></div>
      <div v-if="listErr" class="err" style="margin:10px">{{ listErr }}</div>
      <div v-if="!list.length && !listErr" class="empty">No chats here.</div>
      <div v-for="l in list" :key="l.name" class="wl" :class="{ sel: l.name === sel }" tabindex="0" @click="open(l.name)" @keydown.enter="open(l.name)">
        <span class="wav" :style="{ background: avatarColor(l.name) }">{{ initials(l.organization || l.lead_name) }}</span>
        <div class="wb"><div class="wr1"><span class="wn">{{ l.organization || l.lead_name }}</span><span class="wt" :class="{ g: l.last && l.last.type === 'Incoming' }">{{ ago(l.last?.creation || l.modified) }}</span></div>
          <div class="wr2"><span class="wm">{{ l.last ? (l.last.type === 'Outgoing' ? '✓✓ ' : '') + (l.last.message || '') : l.titan_escalation_reason || 'No messages yet' }}</span>
          <span v-if="l.last && l.last.type === 'Incoming'" class="wu">1</span><span v-else-if="l.lead_temperature === 'Hot'" class="tag Hot">Hot</span></div></div>
      </div>
    </div>
    <div class="card thr">
      <template v-if="c">
        <div class="wch"><span class="wav" :style="{ background: avatarColor(c.lead.name) }">{{ initials(c.lead.organization || c.lead.lead_name) }}</span>
          <div style="flex:1;min-width:0"><b style="font-weight:500">{{ c.lead.organization || c.lead.lead_name }}</b><div class="mut sm" style="white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{{ c.lead.mobile_no || 'No number' }}{{ c.lead.source ? ' · ' + c.lead.source : '' }}</div><span class="chip" style="margin-top:2px;display:inline-block">Follow-ups: {{ c.lead.titan_ai_status }}</span></div>
          <button :disabled="!c.can_act" @click="toggle">{{ c.lead.titan_ai_status === 'Active' ? 'Pause follow-ups' : 'Resume follow-ups' }}</button>
          <button class="blk" :disabled="!c.can_act" @click="takeOver">Take over</button></div>
        <div class="msgs" ref="msgs">
          <div class="wsys" style="background:light-dark(#fdf4c5,#2a2a1a)">Messages are saved on the CRM lead{{ boot.zoho_mode === 'Simulated' ? ' · Zoho sync simulated' : '' }}</div>
          <div v-if="!c.messages.length" class="wsys">No messages yet.</div>
          <div v-for="(m, i) in c.messages" :key="i" class="wm2" :class="[m.out ? 'out' : 'in', m.channel === 'Email' && 'mail']">
            <span v-if="m.out && m.by" class="wby">{{ m.by }}</span><b v-if="m.subject" style="display:block">{{ m.subject }}</b>{{ m.text }}<a v-if="m.attach" :href="m.attach" target="_blank" style="display:block">Attachment</a>
            <span class="wtm">{{ m.channel === 'Email' ? 'Email · ' : '' }}{{ time(m.at) }}{{ m.out ? ' ✓✓' : '' }}</span></div>
          <div v-if="c.lead.titan_escalation_reason" class="wsys">Escalated to sales: {{ c.lead.titan_escalation_reason }} <button style="min-height:24px;font-size:12px;margin-left:6px" @click="resolve">Mark handled</button></div>
        </div>
        <div v-if="!c.in_window && channel === 'WhatsApp'" class="wsys" style="margin:6px auto">More than 24 h since the customer's last message: choose an approved template.</div>
        <form class="wcmp" @submit.prevent="send">
          <select v-model="channel" aria-label="Channel"><option>WhatsApp</option><option>Email</option></select>
          <select v-if="channel === 'WhatsApp' && !c.in_window" v-model="template" aria-label="Template"><option value="">Choose template…</option><option v-for="t in c.templates" :key="t">{{ t }}</option></select>
          <input v-else v-model="text" :placeholder="`Message as ${boot.full_name || 'you'} (pauses automatic follow-ups)`" aria-label="Message" />
          <button class="wsend" :disabled="busy || !c.can_act" aria-label="Send"><svg viewBox="0 0 24 24"><path d="M3 20l18-8L3 4l2 7 9 1-9 1z"/></svg></button>
        </form>
        <form v-if="boot.is_manager && waSim" class="wcmp" style="border-top:1px solid var(--line)" @submit.prevent="simIn"><span class="mut sm">Test: customer says</span><input v-model="simText" placeholder="Simulated incoming message" /><button>Add</button></form>
      </template>
      <div v-else class="empty" style="margin:auto">{{ convErr || 'Choose a chat.' }}</div>
    </div>
    <div class="card pad spec">
      <template v-if="c">
        <div style="display:flex;justify-content:space-between;gap:8px"><div><h2 style="font-size:17px">Requirement sheet</h2><div class="mut sm">{{ c.completeness }}% captured</div></div><span v-if="c.lead.lead_temperature" class="tag" :class="c.lead.lead_temperature">{{ c.lead.lead_temperature }}</span></div>
        <div class="tr"><i :style="{ width: c.completeness + '%', background: '#25a35a' }"></i></div>
        <h3>Product line</h3>
        <select v-model="line" :disabled="!c.can_act" style="width:100%" @change="saveSpec"><option value="">Choose…</option><option v-for="p in c.product_lines" :key="p">{{ p }}</option></select>
        <template v-if="c.spec.length"><h3>Details</h3>
          <dl><template v-for="f in c.spec" :key="f.fieldname"><dt>{{ f.label }}</dt><dd><input v-model="vals[f.fieldname]" :placeholder="f.required ? 'Missing' : ''" :disabled="!c.can_act" @change="saveSpec" :aria-label="f.label" /></dd></template></dl></template>
        <h3>Status</h3>
        <dl><dt>Owner</dt><dd>{{ c.lead.lead_owner || 'Unassigned' }}</dd><dt>Stage</dt><dd>{{ c.lead.status }}</dd><dt>Next follow-up</dt><dd>{{ c.lead.titan_next_followup || '—' }}</dd><dt>Zoho ID</dt><dd>{{ c.lead.titan_zoho_id || '—' }}</dd></dl>
        <div class="acts"><router-link to="/calendar"><button>Book a call</button></router-link><a :href="`/crm/leads/${c.lead.name}`"><button>Open in CRM</button></a></div>
      </template>
    </div>
  </div>
</template>
<script setup>
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ago, api, avatarColor, initials, time } from '../api'
import { store, toast } from '../store'
import { act } from '../use'
const route = useRoute(), router = useRouter()
const boot = computed(() => store.boot)
const views = ['Needs human', 'Following up', 'All']
const view = ref('All'), q = ref(''), list = ref([]), listErr = ref(''), sel = ref(route.params.lead || null)
const c = ref(null), convErr = ref(''), text = ref(''), template = ref(''), channel = ref('WhatsApp'), busy = ref(false), simText = ref(''), msgs = ref(null)
const line = ref(''), vals = reactive({}), waSim = ref(false)
let t
const debounced = () => { clearTimeout(t); t = setTimeout(loadList, 250) }
async function loadList() {
  try { list.value = await api.inbox(view.value === 'Following up' ? 'AI active' : view.value, q.value || null); listErr.value = ''
    if (!sel.value && list.value[0]) open(list.value[0].name, true) } catch (e) { listErr.value = e.message }
}
async function open(name, silent) {
  sel.value = name; if (!silent) router.replace(`/inbox/${name}`)
  try { setConv(await api.conversation(name)); convErr.value = '' } catch (e) { c.value = null; convErr.value = e.message }
}
function setConv(x) {
  c.value = x; line.value = x.lead.titan_product_line || ''
  Object.keys(vals).forEach((k) => delete vals[k]); x.spec.forEach((f) => (vals[f.fieldname] = f.value || ''))
  nextTick(() => msgs.value && (msgs.value.scrollTop = msgs.value.scrollHeight))
}
async function send() {
  if (busy.value) return; busy.value = true
  try { setConv(await act(api.sendReply({ lead: sel.value, text: text.value, channel: channel.value, template: template.value || null }), 'Sent')); text.value = ''; template.value = ''; loadList() } catch {} finally { busy.value = false }
}
async function saveSpec() { try { setConv(await act(api.updateSpec(sel.value, line.value || null, { ...vals }))) } catch {} }
async function toggle() { await act(api.toggleAi(sel.value)); open(sel.value, true) }
async function takeOver() { await act(api.takeOver(sel.value), 'You own this lead now; follow-ups paused'); open(sel.value, true); loadList() }
async function resolve() { setConv(await act(api.resolve(sel.value), 'Marked as handled')); loadList() }
async function simIn() { if (!simText.value) return; setConv(await act(api.simulateIncoming(sel.value, simText.value))); simText.value = ''; loadList() }
onMounted(async () => { loadList(); if (sel.value) open(sel.value, true); try { waSim.value = (await api.whatsapp()).mode === 'Simulated' } catch {} })
watch(() => route.params.lead, (v) => v && v !== sel.value && open(v, true))
</script>
