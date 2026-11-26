<template>
  <h2 class="hello" style="margin-top:0">Settings</h2><p class="lede">Your follow-up timing. Site-wide settings are in <a href="/app/titan-desk-settings">Titan Desk Settings</a>; roles in <a href="/app/user">Users &amp; Permissions</a>.</p>
  <div v-if="error" class="err">{{ error }}</div>
  <form v-if="p" class="card pad" style="max-width:560px;display:grid;gap:12px" @submit.prevent="save">
    <label>Follow-up intervals (hours) <input v-model="p.followup_hours" :placeholder="`Site default: ${p.default_hours}`" style="width:100%" /></label>
    <label>Maximum follow-ups <input v-model="p.max_followups" type="number" min="1" :placeholder="`Site default: ${p.default_max}`" style="width:100%" /></label>
    <div style="display:flex;gap:10px"><label style="flex:1">Quiet hours from <input v-model="p.quiet_start" type="time" style="width:100%" /></label><label style="flex:1">to <input v-model="p.quiet_end" type="time" style="width:100%" /></label></div>
    <label><input v-model="p.enabled" type="checkbox" :true-value="1" :false-value="0" /> Use my own timing</label>
    <div><button class="blk">Save</button></div>
  </form>
  <div v-if="boot.is_manager" class="card pad" style="max-width:560px;margin-top:14px"><h3 style="font-size:16px">Demo data</h3><p class="mut">Load sample Zoho leads and conversations into this site (simulated Zoho, simulated WhatsApp only).</p><button @click="seed">Load demo data</button></div>
</template>
<script setup>
import { computed } from 'vue'
import { api } from '../api'
import { store } from '../store'
import { act, useLoad } from '../use'
const boot = computed(() => store.boot)
const { data: p, error, load } = useLoad(async () => { const r = await api.myPref(); r.enabled ??= 1; return r })
async function save() { try { await act(api.setMyPref({ followup_hours: p.value.followup_hours, max_followups: p.value.max_followups, quiet_start: p.value.quiet_start, quiet_end: p.value.quiet_end, enabled: p.value.enabled }), 'Saved'); load() } catch {} }
async function seed() { try { await act(api.seedDemo(), 'Demo data loaded') } catch {} }
</script>
