<template>
  <div class="calw">
    <div class="card pad"><h2 style="font-size:16px">Calls to schedule <span class="mut" style="font-weight:400">{{ d?.to_schedule.length || 0 }}</span></h2>
      <div class="mut sm">Drag onto a time to book a 30-minute call. Follow-ups for that lead pause until then.</div>
      <div v-for="u in d?.to_schedule || []" :key="u.lead" class="uc" draggable="true" @dragstart="drag = u.lead"><b style="font-weight:500;display:block">{{ u.title }}</b><div class="mut sm">{{ u.reason }}</div></div>
      <p v-if="d && !d.to_schedule.length" class="mut">All escalated leads have a call booked.</p>
    </div>
    <div class="card" style="overflow:hidden">
      <div class="calh"><h2 style="font-size:19px">{{ title }}</h2><button @click="shift(0)">Today</button><button aria-label="Previous" @click="shift(-1)">‹</button><button aria-label="Next" @click="shift(1)">›</button><span class="sp"></span>
        <span class="chip"><i style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#2b63c6"></i> Calls</span><span class="chip"><i style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#8b5cf6"></i> Follow-ups</span>
        <div class="seg"><button :class="{ on: view === 'week' }" @click="view = 'week'; load()">Week</button><button :class="{ on: view === 'month' }" @click="view = 'month'; load()">Month</button></div></div>
      <div v-if="error" class="err" style="margin:12px">{{ error }}</div>
      <div v-if="view === 'week'" class="wk">
        <div class="hd2 tm">IST</div><div v-for="day in days" :key="+day" class="hd2" :class="{ now: same(day, new Date()) }">{{ day.toLocaleDateString('en-IN', { weekday: 'short' }) }} {{ day.getDate() }}</div>
        <template v-for="h in hours" :key="h"><div class="tm">{{ h > 12 ? h - 12 : h }} {{ h >= 12 ? 'PM' : 'AM' }}</div>
          <div v-for="day in days" :key="+day + '-' + h" class="slot" :class="{ over: overKey === key(day, h) }" @dragover.prevent="overKey = key(day, h)" @dragleave="overKey = null" @drop="drop(day, h)">
            <span v-for="e in at(day, h)" :key="e.id" class="ev" :class="e.kind" :title="e.title"><i :style="{ background: e.kind === 'call' ? '#2b63c6' : '#8b5cf6' }"></i>{{ e.title }}</span></div></template>
      </div>
      <div v-else class="mo">
        <div v-for="w in ['Mon','Tue','Wed','Thu','Fri','Sat','Sun']" :key="w" class="mut" style="min-height:0">{{ w }}</div>
        <div v-for="day in monthDays" :key="+day" :class="{ out: day.getMonth() !== cursor.getMonth(), td: same(day, new Date()) }"><div class="mut"><span>{{ day.getDate() }}</span></div>
          <span v-for="e in onDay(day)" :key="e.id" class="ev" :class="e.kind"><i :style="{ background: e.kind === 'call' ? '#2b63c6' : '#8b5cf6' }"></i>{{ e.title }}</span></div>
      </div>
    </div>
  </div>
</template>
<script setup>
import { computed, onMounted, ref } from 'vue'
import { api } from '../api'
import { act } from '../use'
const view = ref('week'), cursor = ref(new Date()), d = ref(null), error = ref(''), drag = ref(null), overKey = ref(null)
const hours = [9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19]
const monday = (x) => { const r = new Date(x); r.setHours(0, 0, 0, 0); r.setDate(r.getDate() - ((r.getDay() + 6) % 7)); return r }
const addD = (x, n) => { const r = new Date(x); r.setDate(r.getDate() + n); return r }
const days = computed(() => [...Array(7)].map((_, i) => addD(monday(cursor.value), i)))
const monthDays = computed(() => { const f = new Date(cursor.value.getFullYear(), cursor.value.getMonth(), 1); const s = monday(f); return [...Array(42)].map((_, i) => addD(s, i)) })
const ymd = (x) => `${x.getFullYear()}-${String(x.getMonth() + 1).padStart(2, '0')}-${String(x.getDate()).padStart(2, '0')}`
const same = (a, b) => ymd(a) === ymd(b)
const key = (day, h) => ymd(day) + 'T' + h
const title = computed(() => cursor.value.toLocaleDateString('en-IN', { month: 'long', year: 'numeric' }))
const parse = (s) => new Date(String(s).replace(' ', 'T'))
const at = (day, h) => (d.value?.events || []).filter((e) => { const x = parse(e.start); return same(x, day) && x.getHours() === h })
const onDay = (day) => (d.value?.events || []).filter((e) => same(parse(e.start), day))
async function load() {
  const [s, e] = view.value === 'week' ? [days.value[0], days.value[6]] : [monthDays.value[0], monthDays.value[41]]
  try { d.value = await api.calendar(ymd(s), ymd(e)); error.value = '' } catch (x) { error.value = x.message }
}
function shift(n) { cursor.value = n === 0 ? new Date() : view.value === 'week' ? addD(cursor.value, 7 * n) : new Date(cursor.value.getFullYear(), cursor.value.getMonth() + n, 1); load() }
async function drop(day, h) { overKey.value = null; if (!drag.value) return
  try { const r = await act(api.bookCall(drag.value, `${ymd(day)} ${String(h).padStart(2, '0')}:00:00`), 'Call booked; follow-ups paused for this lead'); if (r.clash) act(Promise.resolve(), 'Note: this overlaps another of your calls') } catch {}
  drag.value = null; load() }
onMounted(load)
</script>
