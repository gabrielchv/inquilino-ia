<script setup>
import CitationBadge from './CitationBadge.vue'

defineProps({
  message: { type: Object, required: true },
})

const emit = defineEmits(['show-source'])
</script>

<template>
  <div class="flex" :class="message.role === 'user' ? 'justify-end' : 'justify-start'">
    <div
      class="max-w-lg rounded-2xl px-4 py-3"
      :class="
        message.role === 'user'
          ? 'bg-slate-900 text-white'
          : 'border border-slate-200 bg-white text-slate-800'
      "
    >
      <p class="whitespace-pre-wrap text-sm leading-relaxed">
        {{ message.text }}<span v-if="message.streaming" class="animate-pulse">▍</span>
      </p>

      <div v-if="!message.streaming && message.role === 'assistant'" class="mt-2">
        <p
          v-if="message.refused"
          class="text-xs italic text-slate-500"
        >
          Pergunta fora do escopo da Lei do Inquilinato -- recusa deliberada, não uma falha.
        </p>

        <p
          v-else-if="message.citations.length === 0"
          class="rounded-md bg-red-50 px-2 py-1 text-xs text-red-700"
        >
          Esta resposta não pôde ser confirmada nas fontes.
        </p>

        <div v-else class="flex flex-wrap gap-1.5">
          <CitationBadge
            v-for="(citation, i) in message.citations"
            :key="i"
            :citation="citation"
            @show-source="emit('show-source', citation)"
          />
        </div>
      </div>
    </div>
  </div>
</template>
