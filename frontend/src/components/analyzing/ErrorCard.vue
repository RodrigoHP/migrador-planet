<template>
  <div class="detail-card detail-card--error" role="alert" aria-live="assertive">
    <div class="detail-card__header">
      <div class="detail-card__label detail-card__label--red">
        Falha no estágio {{ error.stage }}
      </div>
      <div class="detail-card__title-row">
        <div class="detail-card__pulse detail-card__pulse--red" aria-hidden="true" />
        <h2 class="detail-card__title">{{ error.stageName }} — Falha</h2>
      </div>
      <p class="detail-card__subtitle">
        O sistema tentou automaticamente {{ error.retriesAttempted }} {{ error.retriesAttempted === 1 ? 'vez' : 'vezes' }} sem sucesso
      </p>
    </div>

    <div class="error-content">
      <div class="error-what">
        <div class="error-what__title">O que aconteceu?</div>
        <div class="error-what__text">{{ error.errorMessage }}</div>
      </div>

      <div class="error-actions">
        <button class="error-btn" @click="$emit('decide', 'retry')">
          <div class="error-btn__icon error-btn__icon--retry" aria-hidden="true">&#x1F504;</div>
          <div class="error-btn__text">
            <div class="error-btn__title">Tentar novamente</div>
            <div class="error-btn__desc">Reexecutar a análise. O progresso anterior é mantido.</div>
          </div>
        </button>
        <button class="error-btn" @click="$emit('decide', 'fallback')">
          <div class="error-btn__icon error-btn__icon--skip" aria-hidden="true">&#x23ED;&#xFE0F;</div>
          <div class="error-btn__text">
            <div class="error-btn__title">Continuar sem {{ error.service || 'este serviço' }}</div>
            <div class="error-btn__desc">Prosseguir com dados disponíveis. A qualidade pode ser menor.</div>
          </div>
        </button>
        <button class="error-btn" @click="$emit('decide', 'abort')">
          <div class="error-btn__icon error-btn__icon--cancel" aria-hidden="true">&#x274C;</div>
          <div class="error-btn__text">
            <div class="error-btn__title">Cancelar pipeline</div>
            <div class="error-btn__desc">Encerrar o processamento. Você pode tentar novamente mais tarde.</div>
          </div>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { ErrorData } from '@/pages/analyzingPageConstantsV2'

defineProps<{
  error: ErrorData
}>()

defineEmits<{
  decide: [action: 'retry' | 'fallback' | 'abort']
}>()
</script>

<style scoped>
.detail-card {
  background: #fff;
  border-radius: 14px;
  padding: 0;
  box-shadow: 0 2px 16px rgba(99, 102, 241, 0.06);
  margin-bottom: 20px;
  overflow: hidden;
}

.detail-card--error {
  border: 1.5px solid #fecaca;
}

.detail-card__header {
  padding: 22px 28px 0;
}

.detail-card__label {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin-bottom: 6px;
}

.detail-card__label--red { color: #dc2626; }

.detail-card__title-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 6px;
}

.detail-card__pulse {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  flex-shrink: 0;
}

.detail-card__pulse--red {
  background: #ef4444;
}

.detail-card__title {
  font-size: 19px;
  font-weight: 600;
  color: #1e293b;
  margin: 0;
}

.detail-card__subtitle {
  font-size: 14px;
  color: #64748b;
  margin-bottom: 18px;
  padding-left: 24px;
}

.error-content {
  padding: 0 28px 24px;
}

.error-what {
  background: #fef2f2;
  border-radius: 8px;
  padding: 14px 18px;
  margin-bottom: 18px;
}

.error-what__title {
  font-size: 12px;
  font-weight: 600;
  color: #991b1b;
  margin-bottom: 4px;
}

.error-what__text {
  font-size: 13px;
  color: #7f1d1d;
  line-height: 1.5;
}

.error-actions {
  display: flex;
  gap: 10px;
  flex-direction: column;
}

.error-btn {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 18px;
  border-radius: 10px;
  border: 1.5px solid #e2e8f0;
  background: #fff;
  cursor: pointer;
  transition: all 0.15s;
  text-align: left;
  width: 100%;
}

.error-btn:hover {
  border-color: #c7d2fe;
  background: #faf5ff;
}

.error-btn:focus-visible {
  outline: 2px solid #6366f1;
  outline-offset: 2px;
}

.error-btn__icon {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  flex-shrink: 0;
}

.error-btn__icon--retry { background: #dbeafe; }
.error-btn__icon--skip { background: #fef3c7; }
.error-btn__icon--cancel { background: #fef2f2; }

.error-btn__text {
  flex: 1;
}

.error-btn__title {
  font-size: 14px;
  font-weight: 600;
  color: #1e293b;
}

.error-btn__desc {
  font-size: 12px;
  color: #64748b;
  margin-top: 2px;
}
</style>
