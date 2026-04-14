# Epic 38 — Features Avançadas (Tematização, Bibliotecas, Vision AI)

**Prioridade:** P3
**Fase:** 4
**Estimativa:** 6 stories (originalmente 7 — 38.4 removida, funcionalidade coberta por componentes existentes)
**Dependências:** Epics 31-34 (core funcional)
**Objetivo:** Features de longo prazo que enriquecem o produto mas não são bloqueantes para o uso core: matching por embeddings, tematização condicional, biblioteca de snippets, geração sintética.

---

## Contexto

Estas features foram planejadas no PRD v3 mas não implementadas. Algumas requerem spikes técnicos (Vision AI + pgvector) e outras são extensões significativas da UI (tematização, biblioteca de snippets). O matching atual por LLM (Gemini Flash) funciona — pgvector seria otimização.

---

## Stories

### 38.1 — Spike: Avaliar Vision AI + pgvector para matching semântico
**Gap:** C9
**Escopo:** Backend (investigação/PoC)
**AC:**
- [ ] Documentar custo/benefício de pgvector + embeddings vs LLM text-only atual
- [ ] PoC com 3 documentos reais: medir precisão do matching atual vs com embeddings
- [ ] Medir latência e custo por documento processado
- [ ] Decisão: GO (implementar) / NO-GO (manter LLM text-only) com justificativa
- [ ] Se GO: definir arquitetura (pgvector em Supabase, modelo de embedding, pipeline de indexação)
- [ ] Se NO-GO: documentar razão e marcar FR4 como "atendido com LLM" no PRD

### 38.2 — Tematização condicional (FR30) — runtime only
**Gap:** I32
**Escopo:** Frontend (`baseJsGenerators.ts`) + Backend (stage5)
**QA Note:** UI do rule builder (`ConditionalStyleSection.vue`) **já existe**. Gap é apenas `baseJsGenerators` + runtime no template exportado.
**AC:**
- [ ] `ConditionalStyleSection.vue` já existe — verificar que construtor de regras funciona
- [ ] `baseJsGenerators.ts` gera função `applyConditionalStyle()` no base.js
- [ ] Propriedades condicionais: cor de texto, cor de fundo, src de imagem/logo
- [ ] Template exportado aplica estilos condicionais em runtime via `applyConditionalStyle()`
- [ ] Preview inline mostrando variação visual (se não implementado no existente)

### 38.3 — Biblioteca de snippets/componentes estruturais
**Gap:** C22
**Escopo:** Frontend (`BibliotecasModal.vue`, `useBibliotecas.ts`)
**AC:**
- [ ] 4a categoria no modal: "Componentes" (além de Fontes, CSS, JS)
- [ ] "Salvar como componente" no context menu da árvore: serializa nó + filhos como JSON
- [ ] Componentes listados no modal com preview HTML miniatura
- [ ] "Inserir" adiciona componente como filho do nó selecionado via `templateStore.addNode()`
- [ ] Persistência via IndexedDB (mesma infra de useBibliotecas)
- [ ] Import/Export de biblioteca completa como ZIP

### ~~38.4~~ — REMOVIDA (funcionalidade coberta por componentes existentes)
> Layout Variants Explorer descartado — MultiDocAnalyzer (detecção automática de variações) + DiffViewer (inferências Confirmar/Rejeitar) + Inspector (VisibilityControl para condicionais) já cobrem o caso de uso. Painel separado seria redundante.

### 38.5 — Geração sintética de dados a partir do XSD (FR2b)
**Gap:** I1
**Escopo:** Backend (novo service)
**AC:**
- [ ] Service `xsd_synthetic_generator.py` parseia XSD e gera JSON de exemplo
- [ ] Valores coerentes por tipo: `xs:string` → texto legível, `xs:date` → data válida, `xs:decimal` → número formatado
- [ ] Tipos BR: CPF, CNPJ, CEP, telefone com formato real (válidos mas fictícios)
- [ ] Arrays geram 3-5 elementos por padrão
- [ ] Resultado disponível como `exemplo.js` no pipeline result
- [ ] testDataStore pode usar dados gerados automaticamente

### 38.6 — Persistir `template_name` no job_state e propagar ao pipeline
**Gap:** I2
**Escopo:** Backend (`upload.py`, `analyze.py`)
**QA Note:** `template_name` **já é aceito** no upload. Gap: não persiste no `job_state` nem propaga ao pipeline result.
**AC:**
- [ ] `template_name` persistido no `job_state` durante upload (hoje aceito mas não salvo)
- [ ] Propagado para o pipeline result
- [ ] Frontend exibe nome na toolbar e no save do projeto
- [ ] Nome usado como default no filename do ZIP de export

### 38.7 — Avaliar remoção do nível `page` intermediário na árvore
**Gap:** I14
**Escopo:** Backend (`stage3_structural_analysis.py`) + Frontend
**AC:**
- [ ] Avaliar impacto em: `usePagination.ts`, `HTMLCanvas.vue`, `stage5_template_generation.py`
- [ ] Se seguro aplanar: remover nível `page` → `document > header/flow/footer > elementos`
- [ ] Se não seguro: documentar ADR explicando por que `page` é necessário
- [ ] Árvore exibe hierarquia conforme decisão (com ou sem page)
- [ ] Nenhuma regressão em paginação ou Canvas
