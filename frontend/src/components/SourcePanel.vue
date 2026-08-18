<script setup>
defineProps({
  citation: { type: Object, default: null },
})

const emit = defineEmits(['close'])
</script>

<template>
  <Transition name="slide">
    <aside
      v-if="citation"
      class="fixed inset-y-0 right-0 z-20 flex w-full max-w-md flex-col border-l border-slate-200 bg-white shadow-xl"
    >
      <header class="flex items-center justify-between border-b border-slate-200 p-4">
        <h2 class="font-semibold text-slate-900">Art. {{ citation.artigo }} da Lei 8.245/1991</h2>
        <button
          type="button"
          class="rounded-full p-1 text-slate-500 hover:bg-slate-100"
          @click="emit('close')"
        >
          ✕
        </button>
      </header>
      <div class="flex-1 overflow-y-auto p-4">
        <p class="text-sm leading-relaxed text-slate-700">
          {{ citation.texto_artigo || 'Texto do artigo indisponível.' }}
        </p>
        <div v-if="citation.trecho" class="mt-4 rounded-md bg-slate-50 p-3">
          <p class="mb-1 text-xs font-medium uppercase tracking-wide text-slate-500">
            Trecho citado na resposta
          </p>
          <p class="text-sm italic text-slate-700">"{{ citation.trecho }}"</p>
        </div>
      </div>
    </aside>
  </Transition>
</template>

<style scoped>
.slide-enter-active,
.slide-leave-active {
  transition: transform 0.2s ease;
}
.slide-enter-from,
.slide-leave-to {
  transform: translateX(100%);
}
</style>
