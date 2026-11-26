<template>
  <h2 class="hello" style="margin-top:0">WhatsApp Business</h2>
  <p class="lede">Runs on the WhatsApp app installed on this site (frappe_whatsapp) and Meta's WhatsApp Cloud API.</p>
  <div v-if="error" class="err">{{ error }}</div>
  <template v-else-if="d">
    <div v-if="!d.installed" class="note warn">The WhatsApp app is not installed on this site.</div>
    <template v-else>
      <div v-if="d.mode === 'Simulated'" class="note"><span>ⓘ</span><span>Simulated mode: messages are saved but not sent to Meta. Switch to Live in Titan Desk Settings once the Meta business is verified.</span></div>
      <div v-if="d.other_autoreply" class="note warn"><span>⚠</span><span>Another app may also auto-reply on this number. Check the WhatsApp chatbot app so customers don't get two answers.</span></div>
      <div class="kpis"><div class="kpi"><span class="mut">Accounts</span><b>{{ d.accounts.length }}</b></div><div class="kpi"><span class="mut">Approved templates</span><b>{{ d.templates.filter((t) => t.status === 'APPROVED').length }}/{{ d.templates.length }}</b></div>
        <div class="kpi"><span class="mut">Today in / out</span><b>{{ d.today.in }} / {{ d.today.out }}</b></div><div class="kpi"><span class="mut">Failed today</span><b>{{ d.today.failed }}</b></div></div>
      <div class="two" style="margin-top:0">
        <div class="card pad"><h2 style="font-size:18px">How it works</h2><ol class="mut" style="padding-left:18px;line-height:1.7">
          <li>Meta sends customer messages to the site's webhook; each becomes a WhatsApp Message linked to the CRM lead.</li>
          <li>The desk checks escalation rules on every incoming message and resets follow-ups.</li>
          <li>Replies are sent by creating an outgoing WhatsApp Message.</li>
          <li>Within 24 h of the customer's last message you can send free text; after that only approved templates.</li>
          <li>Meta reports Sent, Delivered, Read or Failed back on each message.</li></ol></div>
        <div class="card"><div class="hd"><h2 style="font-size:18px">Templates</h2><a href="/app/whatsapp-templates"><button>Manage</button></a></div>
          <table><thead><tr><th>Template</th><th>Category</th><th>Status</th></tr></thead><tbody>
          <tr v-for="t in d.templates" :key="t.name"><td>{{ t.template_name || t.name }}</td><td>{{ t.category }}</td><td>{{ t.status }}</td></tr>
          <tr v-if="!d.templates.length"><td colspan="3" class="mut">No templates yet. Create them in WhatsApp Templates and sync from Meta.</td></tr></tbody></table></div>
      </div>
    </template>
  </template>
</template>
<script setup>
import { api } from '../api'
import { useLoad } from '../use'
const { data: d, error } = useLoad(api.whatsapp)
</script>
