<template>
  <div class="app" :class="{ collapsed: store.collapsed }">
    <aside class="side" aria-label="Main navigation">
      <button class="orgsw" type="button" @click.stop="menuOpen = !menuOpen" aria-haspopup="menu">
        <span class="tile" role="img" aria-label="Titan Steel & Engineers"></span>
        <span class="lb ot"><b>Titan Steel &amp; Engineers</b><span>{{ boot.full_name || 'Sales' }}</span></span>
        <Icon class="lb" name="down" />
      </button>
      <template v-for="n in nav" :key="n.label">
        <div v-if="n.group" class="grp"><span>{{ n.group }}</span></div>
        <router-link v-else class="nv" :to="n.to" :title="store.collapsed ? n.label : ''">
          <Icon :name="n.icon" /><span class="lb">{{ n.label }}</span>
          <em v-if="n.count && counts[n.count]" class="lb">{{ counts[n.count] }}</em>
        </router-link>
      </template>
      <a class="nv" href="/crm/leads" title="Open in CRM"><Icon name="lead" /><span class="lb">Leads in CRM</span></a>
      <div class="sfoot">
        <button class="nv" type="button" @click="store.gsOpen = !store.gsOpen" title="Getting started"><Icon name="rocket" /><span class="lb">Getting started</span><kbd class="lb">{{ setup.done }}/{{ setup.total }}</kbd></button>
        <button class="nv" type="button" @click="startTour" title="Take the tour"><Icon name="map" /><span class="lb">Take the tour</span></button>
        <button class="nv" type="button" @click="toggleCollapse" :title="store.collapsed ? 'Expand' : 'Collapse'"><Icon name="side" /><span class="lb">{{ store.collapsed ? 'Expand' : 'Collapse' }}</span></button>
      </div>
    </aside>
    <div>
      <header class="topbar"><h1>{{ route.name }}</h1><button type="button" @click="reload">↻ Refresh</button></header>
      <main class="wrap"><router-view :key="viewKey" /></main>
    </div>

    <div v-if="menuOpen" class="pop" style="left:10px;top:62px" role="menu" @click.stop>
      <div class="mut sm" style="padding:6px 10px">Apps</div>
      <a v-for="a in apps" :key="a.name" class="opt" :href="a.href"><span class="at" :style="{ background: a.color }">{{ a.name[0] }}</span>{{ a.name }}<span v-if="a.current" class="mut sm" style="margin-left:auto">Current</span></a>
      <div style="height:1px;background:var(--line);margin:6px 0"></div>
      <button class="opt" @click="toggleTheme">Toggle theme</button>
      <a class="opt" href="/?cmd=web_logout">Log out</a>
    </div>

    <section v-if="store.gsOpen" class="gs" role="dialog" aria-label="Getting started">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:10px">
        <div><h3 style="font-size:17px">Getting started</h3><div class="mut sm">Welcome to Titan Enquiry Desk</div></div>
        <button type="button" aria-label="Close" @click="store.gsOpen = false">✕</button>
      </div>
      <div class="mut sm" style="margin-top:6px">{{ setup.done }}/{{ setup.total }} steps completed</div>
      <div class="tr"><i :style="{ width: (setup.total ? (100 * setup.done) / setup.total : 0) + '%' }"></i></div>
      <div v-for="s in setup.steps" :key="s.key" class="gsi" :class="{ dn: s.done }">
        <span class="gsc">{{ s.done ? '✓' : '' }}</span>
        <div style="flex:1"><b style="font-weight:500;display:block">{{ s.title }}</b><div class="mut sm">{{ s.done ? 'Done' : s.description }}</div></div>
        <a v-if="!s.done" :href="s.link"><button type="button">Open</button></a>
      </div>
      <button type="button" style="width:100%;margin-top:12px" @click="startTour">Take the 2-minute tour</button>
    </section>

    <Tour />
    <div v-if="store.toast" class="toast" role="status">{{ store.toast }}</div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { api } from './api'
import { store } from './store'
import Icon from './components/Icon.vue'
import Tour from './components/Tour.vue'

const route = useRoute()
const boot = computed(() => store.boot)
const menuOpen = ref(false)
const viewKey = ref(0)
const counts = reactive({ needs: 0, approvals: 0 })
const setup = reactive({ steps: [], done: 0, total: 0 })
const nav = [
  { label: 'Today', to: '/today', icon: 'today' },
  { label: 'Calendar', to: '/calendar', icon: 'cal' },
  { group: 'Sell' },
  { label: 'Inbox', to: '/inbox', icon: 'inbox', count: 'needs' },
  { label: 'Pipeline', to: '/pipeline', icon: 'pipe' },
  { label: 'Approvals', to: '/approvals', icon: 'check', count: 'approvals' },
  { group: 'Channels' },
  { label: 'WhatsApp', to: '/whatsapp', icon: 'wa' },
  { group: 'Run' },
  { label: 'Settings', to: '/settings', icon: 'gear' },
]
const apps = [
  { name: 'Titan Enquiry Desk', href: '/titan-desk', color: '#e8640c', current: true },
  { name: 'CRM', href: '/crm', color: '#d946ef' },
  { name: 'Helpdesk', href: '/helpdesk', color: '#7c3aed' },
  { name: 'Desk', href: '/app', color: '#6b7280' },
  { name: 'ERPNext', href: '/app/home', color: '#2b7ff0' },
]

async function refreshSide() {
  try {
    const t = await api.today()
    counts.needs = t.needs.length
    counts.approvals = t.pending_approvals
    Object.assign(setup, t.setup)
  } catch {}
}
function reload() { viewKey.value++; refreshSide() }
function toggleCollapse() { store.collapsed = !store.collapsed; localStorage.setItem('titan.collapsed', store.collapsed ? '1' : '0') }
function toggleTheme() { const d = document.documentElement; d.dataset.theme = d.dataset.theme === 'dark' ? 'light' : 'dark'; localStorage.setItem('titan.theme', d.dataset.theme); menuOpen.value = false }
function startTour() { store.gsOpen = false; store.tour = 0 }
onMounted(async () => {
  const th = localStorage.getItem('titan.theme'); if (th) document.documentElement.dataset.theme = th
  document.addEventListener('click', () => (menuOpen.value = false))
  if (!store.boot.user) { try { store.boot = await api.boot() } catch {} }
  await refreshSide()
  if (!localStorage.getItem('titan.toured')) { localStorage.setItem('titan.toured', '1'); store.tour = 0 }
  else if (setup.done < setup.total && !sessionStorage.getItem('titan.gsShown')) { sessionStorage.setItem('titan.gsShown', '1'); store.gsOpen = true }
})
</script>
