<template>
  <h2 class="hello" style="margin-top:0">Pipeline</h2><p class="lede">Drag a lead to another stage, or use the stage menu on the card. Changes are sent to Zoho.</p>
  <div v-if="error" class="err">{{ error }}</div>
  <div v-else-if="loading" class="skel" style="height:300px"></div>
  <div v-else class="board">
    <div v-for="st in d.stages" :key="st" class="col" :class="{ over: over === st }" @dragover.prevent="over = st" @dragleave="over = null" @drop="drop(st)">
      <h3><span>{{ st }}</span><span class="mut">{{ by(st).length }}</span></h3>
      <div v-for="l in by(st)" :key="l.name" class="jc" draggable="true" @dragstart="drag = l.name">
        <div style="display:flex;justify-content:space-between;gap:6px"><router-link :to="`/inbox/${l.name}`" style="font-weight:500;text-decoration:none">{{ l.organization || l.lead_name }}</router-link><span v-if="l.lead_temperature" class="tag" :class="l.lead_temperature">{{ l.lead_temperature }}</span></div>
        <div class="mut">{{ l.titan_product_line || 'No product line' }} · {{ l.lead_owner || 'Unassigned' }}</div>
        <div class="tr"><i :style="{ width: (l.spec_pct || 0) + '%' }"></i></div><div class="mut sm">Spec {{ l.spec_pct || 0 }}%</div>
        <div v-if="l.titan_escalation_reason" style="margin-top:6px"><span class="chip">{{ l.titan_escalation_reason }}</span></div>
        <select :value="st" style="margin-top:8px;width:100%" aria-label="Move stage" @change="move(l.name, $event.target.value)"><option v-for="s in d.stages" :key="s">{{ s }}</option></select>
      </div>
    </div>
  </div>
</template>
<script setup>
import { ref } from 'vue'
import { api } from '../api'
import { act, useLoad } from '../use'
const { data: d, error, loading, load } = useLoad(api.pipeline)
const drag = ref(null), over = ref(null)
const by = (st) => (d.value?.leads || []).filter((l) => l.status === st)
async function move(lead, status) { const l = d.value.leads.find((x) => x.name === lead); const old = l.status; l.status = status
  try { await act(api.moveStage(lead, status), `Moved to ${status}`) } catch { l.status = old } }
function drop(st) { over.value = null; if (drag.value) move(drag.value, st); drag.value = null }
</script>
