<template><svg viewBox="0 0 24 24" aria-hidden="true" class="ic" v-html="P[name] || ''"></svg></template>
<script setup>
defineProps({ name: String })
const P = {
  today: '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4M9 15l2 2 4-4"/>',
  cal: '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/>',
  inbox: '<path d="M4 5h16v11H8l-4 4z"/>',
  pipe: '<rect x="3" y="4" width="5" height="16" rx="1"/><rect x="10" y="4" width="5" height="11" rx="1"/><rect x="17" y="4" width="4" height="7" rx="1"/>',
  check: '<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20a6.5 6.5 0 0 1 10.5-5.1M15 18l2.2 2.2L22 15.5"/>',
  wa: '<path d="M4 20l1.5-4A8 8 0 1 1 9 19.5z"/>',
  gear: '<circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M5 5l2 2M17 17l2 2M5 19l2-2M17 7l2-2"/>',
  lead: '<circle cx="9" cy="8" r="4"/><path d="M2 21c0-4 3-6 7-6s7 2 7 6"/>',
  rocket: '<path d="M14 4c3-1.5 6-1 6-1s.5 3-1 6l-6 6-5-5z"/><path d="M9 10 5 10l-2 3 4 1M14 15v4l-3 2-1-4"/>',
  map: '<path d="M3 6l6-2 6 2 6-2v14l-6 2-6-2-6 2z"/><path d="M9 4v14M15 6v14"/>',
  side: '<rect x="3.5" y="4.5" width="17" height="15" rx="2"/><path d="M9.5 4.5v15"/>',
  down: '<path d="m6 9 6 6 6-6"/>',
}
</script>
<style>.ic{width:17px;height:17px;stroke:currentColor;fill:none;stroke-width:1.7;flex:none}</style>
