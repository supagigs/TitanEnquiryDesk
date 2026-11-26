<template>
  <div style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:10px;align-items:flex-start"><div><h2 class="hello" style="margin-top:0">Approvals</h2><p class="lede">Follow-ups and drafted replies waiting for a person before they go to the customer.</p></div>
    <div class="seg"><button v-for="s in ['Pending', 'Sent', 'Rejected', 'Failed']" :key="s" :class="{ on: status === s }" @click="status = s; load()">{{ s }}</button></div></div>
  <div v-if="error" class="err">{{ error }}</div>
  <div v-if="list && !list.length" class="card empty">Nothing {{ status.toLowerCase() }}.</div>
  <div v-for="a in list || []" :key="a.name" class="card pad" style="margin-bottom:12px">
    <div style="display:flex;gap:12px;flex-wrap:wrap;align-items:flex-start"><div style="flex:1;min-width:240px">
      <b style="font-weight:600">{{ a.lead_name || a.lead }}</b> <span class="chip">{{ a.channel }}</span> <span class="mut sm">· {{ a.source || 'manual' }} · {{ a.creation?.slice(0, 16) }}</span>
      <textarea v-if="status === 'Pending'" v-model="edits[a.name]" rows="3" style="width:100%;margin-top:8px" :aria-label="`Draft for ${a.lead_name}`"></textarea>
      <p v-else style="margin:8px 0 0;white-space:pre-wrap">{{ a.draft }}</p>
      <div v-if="a.reject_reason" class="mut sm">Reason: {{ a.reject_reason }}</div></div>
      <div v-if="status === 'Pending'" style="display:flex;flex-direction:column;gap:6px;min-width:150px"><button class="blk" @click="decide(a, 'Approved')">Approve &amp; send</button><button @click="reject(a)">Reject…</button><router-link :to="`/inbox/${a.lead}`"><button style="width:100%">Open chat</button></router-link></div></div>
  </div>
</template>
<script setup>
import { reactive, ref } from 'vue'
import { api } from '../api'
import { act, useLoad } from '../use'
const status = ref('Pending'), edits = reactive({})
const { data: list, error, load } = useLoad(async () => { const r = await api.approvals(status.value); r.forEach((a) => (edits[a.name] = a.draft)); return r })
async function decide(a, decision, reason) { try { await act(api.decide(a.name, decision, reason, edits[a.name]), decision === 'Approved' ? 'Approved and sent' : 'Rejected'); load() } catch {} }
function reject(a) { const r = window.prompt('Why reject this reply?'); if (r) decide(a, 'Rejected', r) }
</script>
