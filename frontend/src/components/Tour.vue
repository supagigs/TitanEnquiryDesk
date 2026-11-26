<template>
  <template v-if="store.tour >= 0">
    <div class="tsp" :style="spot"></div>
    <div class="tcard" role="dialog" aria-live="polite" :style="pos" ref="card">
      <button type="button" style="position:absolute;right:12px;top:12px" aria-label="Close tour" @click="end">✕</button>
      <div class="mut">{{ i + 1 }} of {{ steps.length }}</div>
      <h3>{{ s.title }}</h3><p>{{ s.body }}</p>
      <div v-if="s.note" class="tnote">{{ s.note }}</div>
      <div style="display:flex;align-items:center;gap:8px;margin-top:14px">
        <div class="tdots"><i v-for="(_, j) in steps" :key="j" :class="{ on: j === i }"></i></div>
        <button v-if="i" type="button" @click="go(i - 1)">Back</button>
        <button class="blk" type="button" @click="i === steps.length - 1 ? end() : go(i + 1)">{{ i === steps.length - 1 ? 'Finish' : 'Next' }}</button>
      </div>
    </div>
  </template>
</template>
<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { store } from '../store'

const router = useRouter()
const steps = [
  { to: '/today', sel: null, title: 'Welcome to Titan Enquiry Desk', body: 'Every enquiry from Zoho, WhatsApp and email in one place, with what to do next. This tour takes about two minutes.' },
  { to: '/today', sel: '.hero', title: 'Response time', body: 'How fast customers got their first reply this week.' },
  { to: '/today', sel: '[data-tour=needs]', title: 'Needs a person', body: 'Enquiries the desk escalated: price, delivery dates, drawings, complaints. Hottest first.' },
  { to: '/inbox', sel: '.lst', title: 'Inbox', body: 'All WhatsApp chats and emails per lead. Filter to the ones that need a person.' },
  { to: '/inbox', sel: '.thr', title: 'Conversation', body: 'Reply, take over or pause automatic follow-ups. After 24 hours WhatsApp only allows approved templates.' },
  { to: '/inbox', sel: '.spec', title: 'Requirement sheet', body: 'What has been captured for this product line and what is missing. Fill it in as you learn more.' },
  { to: '/pipeline', sel: '.board', title: 'Pipeline', body: 'Drag a lead between stages. Changes are sent back to Zoho.' },
  { to: '/calendar', sel: '.calw', title: 'Calendar', body: 'Drag a lead from Calls to schedule onto a time to book a call. Follow-ups pause until then.' },
  { to: '/approvals', sel: '.wrap', title: 'Approvals', body: 'In supervised mode, automatic follow-ups wait here until someone approves them.' },
  { to: '/settings', sel: '.wrap', title: 'Your follow-up timing', body: 'Set how often your leads are followed up and your quiet hours.' },
]
const i = ref(0)
const s = computed(() => steps[i.value] || steps[0])
const spot = ref({ display: 'none' })
const pos = ref({ left: '50%', top: '30%', transform: 'translateX(-50%)' })
const card = ref(null)
async function go(n) {
  i.value = n; store.tour = n
  if (router.currentRoute.value.path !== steps[n].to) await router.push(steps[n].to)
  setTimeout(place, 350)
}
function place() {
  const el = s.value.sel && document.querySelector(s.value.sel)
  const W = innerWidth, H = innerHeight, cw = card.value?.offsetWidth || 400, ch = card.value?.offsetHeight || 220
  if (!el) { spot.value = { left: '50%', top: '40%', width: 0, height: 0 }; pos.value = { left: (W - cw) / 2 + 'px', top: Math.max(12, (H - ch) / 2) + 'px' }; return }
  el.scrollIntoView({ block: 'center' })
  const r = el.getBoundingClientRect(), t = Math.max(r.top, 4), b = Math.min(r.bottom, H - 4)
  spot.value = { left: r.left - 6 + 'px', top: t - 6 + 'px', width: r.width + 12 + 'px', height: b - t + 12 + 'px' }
  let x = r.left, y = b + 14
  if (y + ch > H - 12) { y = t - ch - 14; if (y < 12) { x = Math.min(r.right + 14, W - cw - 12); y = Math.max(12, Math.min(t, H - ch - 12)) } }
  pos.value = { left: Math.max(12, Math.min(x, W - cw - 12)) + 'px', top: Math.max(12, y) + 'px' }
}
function end() { store.tour = -1; if (!sessionStorage.getItem('titan.gsShown')) { sessionStorage.setItem('titan.gsShown', '1'); store.gsOpen = true } }
function key(e) { if (store.tour < 0 || e.target.closest('input,textarea,select')) return; if (e.key === 'Escape') end(); if (e.key === 'ArrowRight') (i.value === steps.length - 1 ? end() : go(i.value + 1)); if (e.key === 'ArrowLeft' && i.value) go(i.value - 1) }
watch(() => store.tour, (v) => { if (v >= 0 && v !== i.value) go(v); else if (v === 0) nextTick(() => go(0)) })
onMounted(() => { addEventListener('keydown', key); addEventListener('resize', () => store.tour >= 0 && place()); if (store.tour >= 0) go(store.tour) })
onBeforeUnmount(() => removeEventListener('keydown', key))
</script>
