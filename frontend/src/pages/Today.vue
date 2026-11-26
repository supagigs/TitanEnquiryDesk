<template>
  <div v-if="loading" ><div class="skel" v-for="n in 4" :key="n"></div></div>
  <div v-else-if="error" class="err">{{ error }}</div>
  <div v-else-if="d">
    <div v-if="d.supervised" class="note"><span>ⓘ</span><span>Supervised mode is on: automatic follow-ups wait in <router-link to="/approvals">Approvals</router-link> until someone approves them.</span></div>
    <div class="mut">{{ new Date(d.date).toLocaleDateString('en-IN', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' }) }}</div>
    <h2 class="hello">{{ greet }}, {{ first }}. {{ d.needs.length }} {{ d.needs.length === 1 ? 'enquiry needs' : 'enquiries need' }} a person today.</h2>
    <p class="lede">Escalated enquiries first, then leads being followed up automatically, and how the week is going.</p>
    <div class="row3">
      <div class="card hero">
        <h2 style="font-size:21px">{{ d.response.median_minutes != null ? `First replies in ${d.response.median_minutes} min` : 'No replies measured yet' }}</h2>
        <small>{{ d.response.answered || 0 }} of {{ d.response.count }} WhatsApp enquiries answered this week · {{ d.open_count }} open · {{ d.hot_count }} hot</small>
        <div style="font-size:14.5px;color:#dfe8fb">Target: first reply within the response target set in Titan Desk Settings.</div>
      </div>
      <div class="card pad"><div class="cap"><span>THIS WEEK'S GOALS</span></div>
        <div v-for="g in d.goals" :key="g.label" class="goal"><div><span>{{ g.label }}</span><span class="mut">{{ g.done }}/{{ g.target }}</span></div><div class="tr"><i :style="{ width: Math.min(100, (100 * g.done) / (g.target || 1)) + '%' }"></i></div></div>
      </div>
      <div class="card pad"><div class="cap"><span>WHERE ENQUIRIES CAME FROM</span></div>
        <div v-for="(n, k) in d.sources" :key="k" class="hb"><span>{{ k }}</span><div><i :style="{ width: (100 * n) / maxSrc + '%' }"></i></div><b>{{ n }}</b></div>
        <div v-if="!Object.keys(d.sources).length" class="mut">No open enquiries yet.</div>
      </div>
    </div>
    <div class="week"><div v-for="w in d.week" :key="w.date" class="day" :class="{ now: w.date === d.date }">{{ new Date(w.date).toLocaleDateString('en-IN', { weekday: 'short' }).toUpperCase() }}<b>{{ new Date(w.date).getDate() }}</b><small>{{ w.count != null ? w.count + ' new' : '' }}</small></div></div>
    <div data-tour="needs">
      <div style="display:flex;justify-content:space-between;margin:6px 0 8px"><b>Needs a person</b><span class="mut">{{ d.needs.length }} left</span></div>
      <div v-if="!d.needs.length" class="card empty">Nothing escalated right now.</div>
      <div v-for="(l, i) in d.needs" :key="l.name" class="task" :class="{ first: i === 0 }">
        <div style="flex:1;min-width:0"><b style="font-weight:500">{{ l.titan_escalation_reason }}: {{ l.organization || l.lead_name }}</b>
          <div class="mut sm">{{ l.titan_product_line || 'Product not set' }} · {{ l.source || 'Unknown source' }} · {{ l.lead_owner || 'Unassigned' }}</div></div>
        <div class="end"><span v-if="l.lead_temperature" class="tag" :class="l.lead_temperature">{{ l.lead_temperature }}</span><router-link :to="`/inbox/${l.name}`"><button :class="{ blk: i === 0 }">Open chat</button></router-link></div>
      </div>
    </div>
    <div class="two">
      <div class="card"><div class="hd"><h2 style="font-size:18px">Being followed up</h2><span class="mut">{{ d.ai_active.length }}</span></div>
        <div v-if="!d.ai_active.length" class="empty">No leads on automatic follow-up.</div>
        <div v-for="(l, i) in d.ai_active" :key="l.name" class="it"><div class="num">{{ i + 1 }}</div>
          <div style="flex:1;min-width:0"><span class="chip">Spec {{ l.titan_spec_completeness || 0 }}%</span> <span class="mut sm">{{ l.last && l.last.type === 'Incoming' ? 'Customer is waiting for a reply' : l.titan_next_followup ? 'Next follow-up ' + new Date(l.titan_next_followup.replace(' ', 'T')).toLocaleString('en-IN', { weekday: 'short', hour: '2-digit', minute: '2-digit' }) : 'No follow-up scheduled' }}</span>
            <div style="font-weight:500;margin:4px 0 2px">{{ l.organization || l.lead_name }}</div><div class="mut sm">Missing: {{ l.missing.join(', ') || 'nothing' }}</div></div>
          <router-link :to="`/inbox/${l.name}`"><button class="blk">Open</button></router-link></div>
      </div>
      <div class="card"><div class="hd"><h2 style="font-size:18px">Product lines</h2></div>
        <div class="pad"><div v-for="(n, k) in d.lines" :key="k" class="hb"><span>{{ k }}</span><div><i :style="{ width: (100 * n) / maxLine + '%' }"></i></div><b>{{ n }}</b></div>
        <div v-if="!Object.keys(d.lines).length" class="mut">Set a product line on a lead's requirement sheet to see it here.</div></div></div>
    </div>
  </div>
</template>
<script setup>
import { computed } from 'vue'
import { api } from '../api'
import { useLoad } from '../use'
const { data: d, error, loading } = useLoad(api.today)
const first = computed(() => { const n = d.value?.user || ''; const f = n.split(' ')[0]; return (f.endsWith('.') ? n : f).replace(/\.$/, '') })
const greet = computed(() => { const h = new Date().getHours(); return h < 12 ? 'Good morning' : h < 17 ? 'Good afternoon' : 'Good evening' })
const maxSrc = computed(() => Math.max(1, ...Object.values(d.value?.sources || {})))
const maxLine = computed(() => Math.max(1, ...Object.values(d.value?.lines || {})))
</script>
