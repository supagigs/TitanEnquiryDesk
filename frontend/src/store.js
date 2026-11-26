import { reactive } from 'vue'
export const store = reactive({
  boot: window.titan_boot || {},
  toast: '',
  collapsed: localStorage.getItem('titan.collapsed') === '1',
  gsOpen: false,
  tour: -1,
})
let h
export function toast(msg) { store.toast = msg; clearTimeout(h); h = setTimeout(() => (store.toast = ''), 2600) }
