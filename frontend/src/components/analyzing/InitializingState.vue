<template>
  <div class="init-card detail-card detail-card--initializing">
    <div class="detail-card__header">
      <div class="detail-card__label detail-card__label--gray">Preparando pipeline</div>
      <div class="detail-card__title-row">
        <div class="detail-card__pulse detail-card__pulse--gray" aria-hidden="true" />
        <h2 class="detail-card__title detail-card__title--gray">Conectando ao pipeline...</h2>
      </div>
      <p class="detail-card__subtitle">Preparando ambiente de processamento para seus documentos</p>
    </div>
    <div class="detail-card__progress">
      <div class="progress-top">
        <span class="progress-top__sub" style="color: #64748b;">Aguardando início</span>
        <span class="progress-top__pct" style="color: #64748b;">&mdash;</span>
      </div>
      <div class="progress-bar-bg progress-bar-bg--gray">
        <div class="progress-shimmer" />
      </div>
      <div class="progress-footer">
        <span class="progress-footer__time">Calculando tempo estimado...</span>
      </div>
    </div>
  </div>

  <!-- Info Cards -->
  <div class="info-row">
    <div class="info-card">
      <div class="info-card__label">PDFs enviados</div>
      <div class="info-card__value">{{ pdfCount ?? '—' }}</div>
    </div>
    <div class="info-card">
      <div class="info-card__label">Páginas</div>
      <div class="info-card__value info-card__value--pending">—</div>
      <div class="info-card__sub">aguardando extração</div>
    </div>
    <div class="info-card">
      <div class="info-card__label">Layouts</div>
      <div class="info-card__value info-card__value--pending">—</div>
      <div class="info-card__sub">aguardando análise</div>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  pdfCount?: number | null
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

.detail-card--initializing {
  border: 1.5px solid #e2e8f0;
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

.detail-card__label--gray { color: #64748b; }

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

.detail-card__pulse--gray { background: #94a3b8; }

.detail-card__title {
  font-size: 19px;
  font-weight: 600;
  margin: 0;
}

.detail-card__title--gray { color: #64748b; }

.detail-card__subtitle {
  font-size: 14px;
  color: #64748b;
  margin-bottom: 18px;
  padding-left: 24px;
}

.detail-card__progress {
  padding: 0 28px 20px;
}

.progress-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.progress-top__sub {
  font-size: 13px;
  color: #475569;
  font-weight: 500;
}

.progress-top__pct {
  font-size: 14px;
  font-weight: 700;
  color: #6366f1;
}

.progress-bar-bg {
  background: #e0e7ff;
  border-radius: 99px;
  height: 7px;
  overflow: hidden;
}

.progress-bar-bg--gray {
  background: #e2e8f0;
}

.progress-shimmer {
  height: 100%;
  background: linear-gradient(90deg, #e2e8f0 25%, #f1f5f9 50%, #e2e8f0 75%);
  background-size: 400px 100%;
  animation: shimmer 1.5s ease-in-out infinite;
  border-radius: 99px;
}

@keyframes shimmer {
  0% { background-position: -400px 0; }
  100% { background-position: 400px 0; }
}

.progress-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 10px;
}

.progress-footer__time {
  font-size: 12px;
  color: #64748b;
}

/* Info cards */
.info-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-bottom: 20px;
}

.info-card {
  background: #fff;
  border-radius: 10px;
  border: 1px solid #e2e8f0;
  padding: 16px 18px;
}

.info-card__label {
  font-size: 11px;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin-bottom: 6px;
}

.info-card__value {
  font-size: 22px;
  font-weight: 700;
  color: #1e293b;
}

.info-card__value--pending {
  color: #cbd5e1;
}

.info-card__sub {
  font-size: 12px;
  color: #64748b;
  margin-top: 4px;
}
</style>
