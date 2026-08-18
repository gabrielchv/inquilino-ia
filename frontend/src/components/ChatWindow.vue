<script setup>
import { nextTick, ref } from 'vue'
import MessageBubble from './MessageBubble.vue'
import SourcePanel from './SourcePanel.vue'
import { streamChatEvents } from '../composables/useSSE.js'

const messages = ref([])
const question = ref('')
const sending = ref(false)
const activeCitation = ref(null)
const scrollAnchor = ref(null)

async function scrollToEnd() {
  await nextTick()
  scrollAnchor.value?.scrollIntoView({ behavior: 'smooth' })
}

async function send() {
  const text = question.value.trim()
  if (!text || sending.value) return

  question.value = ''
  sending.value = true
  messages.value.push({ role: 'user', text })
  const assistantMessage = {
    role: 'assistant',
    text: '',
    streaming: true,
    citations: [],
    refused: false,
  }
  messages.value.push(assistantMessage)
  scrollToEnd()

  try {
    for await (const { event, data } of streamChatEvents(text)) {
      if (event === 'delta') {
        assistantMessage.text += data.text
        scrollToEnd()
      } else if (event === 'done') {
        assistantMessage.citations = data.citations
        assistantMessage.refused = data.refused
        assistantMessage.streaming = false
      }
    }
  } catch {
    assistantMessage.text = 'Erro ao consultar o assistente. Tente novamente.'
    assistantMessage.streaming = false
  } finally {
    sending.value = false
  }
}
</script>

<template>
  <div class="mx-auto flex h-screen max-w-2xl flex-col">
    <header class="border-b border-slate-200 px-4 py-3">
      <h1 class="text-lg font-semibold text-slate-900">InquilinoIA</h1>
      <p class="text-xs text-slate-500">
        Respostas fundamentadas na Lei do Inquilinato (Lei 8.245/1991), com citação
        obrigatória e verificação automática.
      </p>
    </header>

    <div class="flex-1 space-y-3 overflow-y-auto px-4 py-4">
      <p v-if="messages.length === 0" class="mt-8 text-center text-sm text-slate-400">
        Pergunte, por exemplo: "posso sair do contrato antes do prazo?"
      </p>
      <MessageBubble
        v-for="(message, i) in messages"
        :key="i"
        :message="message"
        @show-source="(citation) => (activeCitation = citation)"
      />
      <div ref="scrollAnchor" />
    </div>

    <form class="flex gap-2 border-t border-slate-200 p-4" @submit.prevent="send">
      <input
        v-model="question"
        type="text"
        placeholder="Digite sua pergunta sobre locação de imóveis..."
        class="flex-1 rounded-full border border-slate-300 px-4 py-2 text-sm outline-none focus:border-slate-500"
        :disabled="sending"
      />
      <button
        type="submit"
        class="rounded-full bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        :disabled="sending || !question.trim()"
      >
        Enviar
      </button>
    </form>

    <SourcePanel :citation="activeCitation" @close="activeCitation = null" />
  </div>
</template>
