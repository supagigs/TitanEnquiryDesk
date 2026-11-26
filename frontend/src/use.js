import { onMounted, ref } from 'vue'
import { toast } from './store'
export function useLoad(fn) {
  const data = ref(null), error = ref(''), loading = ref(true)
  async function load() { loading.value = true; error.value = ''; try { data.value = await fn() } catch (e) { error.value = e.message } finally { loading.value = false } }
  onMounted(load)
  return { data, error, loading, load }
}
export async function act(promise, ok) {
  try { const r = await promise; if (ok) toast(ok); return r } catch (e) { toast(e.message); throw e }
}
