<script setup>
defineProps({
  citation: { type: Object, required: true },
})

const emit = defineEmits(['show-source'])
</script>

<template>
  <button
    type="button"
    class="inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium transition"
    :class="
      citation.verified
        ? 'border-emerald-300 bg-emerald-50 text-emerald-800 hover:bg-emerald-100'
        : 'border-amber-300 bg-amber-50 text-amber-800 hover:bg-amber-100'
    "
    @click="emit('show-source', citation)"
  >
    <span>Art. {{ citation.artigo }}</span>
    <span v-if="citation.verified">✓</span>
    <span v-else>?</span>
  </button>
</template>
