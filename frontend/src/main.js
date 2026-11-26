import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'
import './styles.css'

const routes = [
  { path: '/', redirect: '/today' },
  { path: '/today', name: 'Today', component: () => import('./pages/Today.vue') },
  { path: '/calendar', name: 'Calendar', component: () => import('./pages/Calendar.vue') },
  { path: '/inbox/:lead?', name: 'Inbox', component: () => import('./pages/Inbox.vue') },
  { path: '/pipeline', name: 'Pipeline', component: () => import('./pages/Pipeline.vue') },
  { path: '/approvals', name: 'Approvals', component: () => import('./pages/Approvals.vue') },
  { path: '/whatsapp', name: 'WhatsApp', component: () => import('./pages/WhatsApp.vue') },
  { path: '/settings', name: 'Settings', component: () => import('./pages/Settings.vue') },
  { path: '/:p(.*)*', redirect: '/today' },
]
const router = createRouter({ history: createWebHistory('/titan-desk'), routes })
createApp(App).use(router).mount('#app')
