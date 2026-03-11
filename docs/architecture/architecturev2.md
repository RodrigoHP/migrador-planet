# Arquitetura Técnica V2 — Migrador Planetexpress -> HTML/Knockout.js

**Versão:** 2.0
**Data:** 2026-03-10
**Autor:** @architect (Aria)
**Status:** Proposta

---

## Change Log

| Versão | Data | Descrição |
|--------|------|-----------|
| 2.0 | 2026-03-10 | Nova arquitetura desktop-first com Electron no cliente, FastAPI remoto stateless e Supabase para persistência |

---

## 1. Visão Geral

A V2 substitui a abordagem "web hospedada acessada por browser" por uma abordagem "desktop client + backend remoto". O operador usa uma aplicação instalada em sua máquina, com experiência desktop e acesso facilitado a arquivos locais, enquanto o processamento pesado continua centralizado em um backend Python publicado.

O produto nao precisa operar offline. Portanto, o cliente desktop existe para melhorar experiencia de uso, integracao com filesystem local, controle de atualizacao e sensacao de produto instalado, sem mover a logica critica para dentro do cliente.

```text
+--------------------------- Cliente Desktop ---------------------------+
|                           Electron App                               |
|                                                                      |
|  +----------------------- Renderer (Vue 3) ------------------------+ |
|  | Wizard 0..5                                                    | |
|  | PDF.js                                                         | |
|  | Monaco Editor                                                  | |
|  | Chart.js                                                       | |
|  | Estado local do projeto                                        | |
|  +---------------------------|-------------------------------------+ |
|                              | IPC seguro via preload               |
|  +---------------------------v-------------------------------------+ |
|  | Electron Main                                                 | |
|  | - abrir/salvar arquivos                                      | |
|  | - downloads                                                  | |
|  | - config do endpoint                                         | |
|  | - auto-update                                                | |
|  +---------------------------------------------------------------+ |
+-------------------------------|-------------------------------------+
                                |
                                | HTTPS REST + SSE
                                v
+------------------------- Backend Remoto -----------------------------+
|                         FastAPI / Python                            |
|                                                                     |
|  Routers                                                            |
|  - /upload                                                          |
|  - /analyze                                                         |
|  - /mapping                                                         |
|  - /layout                                                          |
|  - /generate                                                        |
|  - /export                                                          |
|  - /progress/{jobId}                                                |
|                                                                     |
|  Services                                                           |
|  - pdf_extractor                                                    |
|  - xsd_parser                                                       |
|  - ai_matcher                                                       |
|  - ai_vision                                                        |
|  - html/css/js_generator                                            |
|  - zip_builder                                                      |
+-------------------------------|-------------------------------------+
                                |
                                v
+--------------------------- Supabase --------------------------------+
| Postgres                                                            |
| - projects                                                         |
| - project_versions                                                 |
| - jobs                                                             |
| - job_events                                                       |
| - output_refs                                                      |
|                                                                     |
| Storage                                                             |
| - uploads/                                                         |
| - extracted-images/                                                |
| - generated-output/                                                |
| - zip/                                                             |
| - temp/                                                            |
+---------------------------------------------------------------------+
```

---

## 2. Objetivos Arquiteturais

1. Entregar experiencia desktop sem depender de um browser puro.
2. Preservar Python como backend principal para PDF, XSD, IA e geracao.
3. Manter backend stateless para facilitar deploy, escala e resiliencia.
4. Permitir uso simples de arquivos locais pelo operador.
5. Evitar duplicacao de regra critica entre cliente e servidor.
6. Manter um contrato de API unico entre desenvolvimento local e producao.

---

## 3. Comparacao com a V1

| Tema | V1 - Web hospedada | V2 - Desktop + backend remoto |
|------|---------------------|-------------------------------|
| Entrada do usuario | Browser | App Electron instalado |
| UX de arquivos locais | Limitada ao browser | Nativa via shell desktop |
| Distribuicao | URL unica | App cliente + API publicada |
| Atualizacao do cliente | Deploy do frontend | Auto-update do Electron |
| Backend | FastAPI servindo API e frontend | FastAPI servindo apenas API |
| Persistencia operacional | Arquivos e sessoes no servidor | Supabase Postgres + Storage |
| Sensacao de produto | Ferramenta web interna | Aplicacao desktop instalada |
| Complexidade de runtime | Menor | Maior no cliente |
| Aderencia ao objetivo atual | Parcial | Alta |

### 3.1 O que a V2 melhora

1. Melhor experiencia para abrir, salvar e retomar projetos locais.
2. Melhor encaixe com o posicionamento desktop-first desejado.
3. Melhor separacao de responsabilidade entre shell, UI, backend e persistencia.
4. Melhor suporte a atualizacao do cliente e configuracao de endpoint.

### 3.2 O que a V2 adiciona de custo

1. Introduz manutencao de shell desktop.
2. Exige empacotamento e distribuicao do cliente.
3. Aumenta superficie de runtime no frontend com `main`, `preload` e `renderer`.

---

## 4. Decisoes Arquiteturais

### 4.1 Por que Electron

Electron foi escolhido porque o produto precisa de:

1. acesso simples e controlado ao filesystem local
2. experiencia de app instalado
3. estrategia madura de auto-update
4. boa compatibilidade com stack frontend baseada em JavaScript

Trade-off aceito:

1. maior consumo de memoria do que alternativas como Tauri
2. camada adicional de empacotamento

Electron foi considerado mais pragmatico para o contexto atual do time e para integracao com `Vue`, `PDF.js`, `Monaco` e `Chart.js`.

### 4.2 Por que manter Vue 3

Vue continua sendo a melhor escolha para a camada de UI porque:

1. ja esta alinhado ao PRD e ao wireframe existentes
2. integra naturalmente com `PDF.js`, `Monaco` e `Chart.js`
3. evita custo de migracao para outro modelo mental
4. reduz atrito em comparacao com `Blazor WASM`, que exigiria maior volume de interop JavaScript

### 4.3 Por que manter Python no backend

Python continua sendo a stack correta para:

1. extracao estruturada com `PyMuPDF`
2. parse de XSD/XML com `lxml`
3. integracao com IA
4. geracao do output HTML/CSS/JS

### 4.4 Por que backend stateless

O backend remoto deve ser stateless para:

1. escalar horizontalmente sem afinidade de sessao
2. tolerar reinicio de instancia sem perda de estado operacional
3. permitir que qualquer instancia atenda qualquer job
4. simplificar deploy e operacao

Estado persistente deve ficar fora da memoria da API.

### 4.5 Por que Supabase

Supabase foi escolhido como infraestrutura de persistencia porque oferece:

1. `Postgres` gerenciado para metadados e jobs
2. `Storage` para uploads e artefatos
3. menor esforco operacional do que hospedar separadamente banco e blob storage

O Supabase nao substitui o backend Python. Seu papel e fornecer persistencia relacional e armazenamento de objetos.

---

## 5. Stack Tecnologica V2

### 5.1 Cliente Desktop

| Tecnologia | Versão | Função |
|------------|--------|--------|
| Electron | 30+ | Shell desktop, updater, janelas |
| Vue 3 | 3.5+ | Framework UI |
| TypeScript | 5.x | Tipagem estática |
| Vite | 6.x | Build e desenvolvimento |
| Pinia | 2.x | Estado do frontend |
| PDF.js | 4.x | Renderizacao e navegacao de PDF |
| Monaco Editor | 0.52+ | Editor embutido |
| Chart.js | 4.x | Preview e configuracao de graficos |

### 5.2 Backend Remoto

| Tecnologia | Versão | Função |
|------------|--------|--------|
| Python | 3.12+ | Linguagem |
| FastAPI | 0.115+ | API REST e SSE |
| Uvicorn | 0.32+ | ASGI server |
| PyMuPDF | 1.24+ | Extracao de PDF |
| lxml | 5.x | Parse de XSD/XML |
| LiteLLM | 1.x | Integracao com modelos |
| Pillow | 10.x | Processamento de imagens |

### 5.3 Persistencia

| Tecnologia | Função |
|------------|--------|
| Supabase Postgres | Metadados, jobs, progresso, versoes, referencias |
| Supabase Storage | Uploads, artefatos gerados, ZIPs, temporarios |

---

## 6. Distribuicao de Responsabilidades

### 6.1 Electron Main

Responsavel por:

1. ciclo de vida do app
2. atualizacao automatica
3. abrir e salvar arquivos
4. downloads
5. configuracao local
6. ponte segura para o renderer

Nao deve conter:

1. parsing de PDF
2. matching
3. geracao do output
4. regras canônicas do produto

### 6.2 Electron Preload

Responsavel por:

1. expor uma API minima e segura para o renderer
2. intermediar acesso ao filesystem
3. proteger o renderer de acesso Node irrestrito

### 6.3 Vue Renderer

Responsavel por:

1. workflow do wizard
2. estado de UI
3. validacoes de experiencia
4. mapeamento manual temporario
5. editor visual
6. integracao com `PDF.js`, `Monaco` e `Chart.js`
7. chamadas REST e SSE

### 6.4 FastAPI

Responsavel por:

1. upload e validacao inicial
2. extracao PDF/XSD/dados
3. matching com IA
4. score de fidelidade
5. geracao de HTML/CSS/JS
6. geracao de ZIP
7. regras oficiais do dominio
8. orquestracao de jobs

### 6.5 Supabase

Responsavel por:

1. persistencia de projetos remotos e jobs
2. trilha de progresso e eventos
3. armazenamento de uploads e outputs

---

## 7. Modelo de Estado

### 7.1 Estado no cliente

O cliente pode ser stateful. Ele deve manter:

1. etapa atual do wizard
2. pagina selecionada
3. drafts locais de edicao
4. configuracao visual ainda nao enviada
5. caminho do projeto local `.json`
6. preferencias de ambiente e endpoint

### 7.2 Estado no backend

O backend nao deve depender de memoria de processo como fonte de verdade. Todo estado operacional deve ser persistido externamente.

### 7.3 Estado persistido

O estado duravel do servidor deve residir em:

1. `projects`
2. `project_versions`
3. `jobs`
4. `job_events`
5. referencias de output
6. uploads e artefatos no storage

---

## 8. Fluxo de Ambientes

### 8.1 Desenvolvimento local

```text
Electron local -> Vue local -> FastAPI local -> Supabase dev
```

No ambiente de desenvolvimento, o renderer aponta para `http://localhost`, preservando o mesmo contrato usado em producao.

### 8.2 Producao

```text
Electron empacotado -> API publicada em HTTPS -> Supabase producao
```

O app cliente usa `API_BASE_URL` configuravel, permitindo troca controlada entre ambientes.

---

## 9. Fluxo Operacional Principal

```text
1. Usuario abre o app Electron
2. Renderer Vue inicia o wizard ou reabre um projeto local
3. Usuario seleciona PDF, XSD e dados no disco local
4. Renderer envia arquivos para o FastAPI
5. FastAPI grava uploads no Supabase Storage
6. FastAPI cria job e metadados no Supabase Postgres
7. Renderer acompanha progresso por SSE usando jobId
8. FastAPI processa, persiste resultados e gera output
9. Renderer recupera resultado final e atualiza o projeto local
10. Usuario baixa ZIP, abre preview ou salva projeto .json
```

---

## 10. Estrutura de Persistencia Remota

### 10.1 Tabelas principais

| Tabela | Finalidade |
|--------|------------|
| `projects` | Registro do projeto remoto |
| `project_versions` | Versionamento do estado processado |
| `jobs` | Controle de execucao |
| `job_events` | Linha do tempo de progresso e eventos |
| `output_refs` | Referencias para artefatos gerados |

### 10.2 Buckets de storage

| Bucket | Finalidade |
|--------|------------|
| `uploads` | PDF, XSD, XML, JSON enviados |
| `extracted-images` | Imagens extraidas do PDF |
| `generated-output` | HTML/CSS/JS gerados |
| `zip` | Pacotes finais |
| `temp` | Artefatos temporarios com TTL |

---

## 11. API e Comunicacao

### 11.1 Endpoints principais

| Método | Rota | Finalidade |
|--------|------|------------|
| `POST` | `/upload/pdf` | Upload do PDF |
| `POST` | `/upload/xsd` | Upload do XSD |
| `POST` | `/upload/data` | Upload dos dados |
| `POST` | `/analyze` | Iniciar analise |
| `GET/PUT` | `/mapping/{session_or_job_id}` | Ler e atualizar mapeamento |
| `GET/PUT` | `/layout/{session_or_job_id}` | Ler e atualizar layout |
| `POST` | `/generate/{session_or_job_id}` | Gerar output |
| `GET` | `/export/{session_or_job_id}/zip` | Download do ZIP |
| `GET` | `/progress/{jobId}` | SSE de progresso |

### 11.2 Comunicacao em tempo real

`SSE` continua adequado para a V2 porque:

1. o fluxo principal e unidirecional
2. o backend precisa publicar progresso incremental
3. o renderer precisa apenas observar eventos por `jobId`

---

## 12. Salvamento de Projeto Local

O operador pode salvar o projeto em um arquivo `.json` local. Esse arquivo deve conter:

1. metadados do projeto
2. caminhos locais de entrada
3. estado do wizard
4. decisoes de mapeamento e layout
5. configuracao de graficos
6. ajustes manuais
7. referencias remotas como `projectId` e `lastJobId`

Esse `.json` nao deve embutir artefatos binarios pesados.

---

## 13. Consideracoes de Seguranca

Mesmo sem aprofundar autenticacao nesta versao, o desenho deve preservar:

1. `contextIsolation=true`
2. `nodeIntegration=false`
3. API de `preload` minima
4. comunicacao HTTPS com backend publicado
5. segregacao clara entre renderer e recursos do sistema operacional

---

## 14. Riscos e Mitigacoes

| Risco | Impacto | Mitigação |
|-------|---------|-----------|
| Aumento de complexidade no cliente | Médio | Limitar responsabilidades do Electron ao shell |
| Duplicacao de regra entre cliente e backend | Alto | Centralizar regra canônica no FastAPI |
| Crescimento de uso de memoria no cliente | Médio | Medir com PDF.js + Monaco + preview realista |
| Acoplamento excessivo ao backend remoto | Baixo | Contrato REST/SSE bem definido e versionado |

---

## 15. ADR — Decisao Arquitetural

### 15.1 Titulo

Adocao de `Electron + Vue + FastAPI + Supabase` em substituicao a arquitetura web hospedada como direcao principal do produto.

### 15.2 Status

Proposto.

### 15.3 Contexto

A V1 assumia um frontend web servido pelo backend e acessado por browser. Essa abordagem mostrou aderencia parcial aos requisitos tecnicos, mas ficou desalinhada ao objetivo de produto desktop-first e ao desejo de facilitar operacoes locais de arquivo sem comprometer o backend remoto.

### 15.4 Decisao

Adotar:

1. cliente desktop em Electron
2. frontend Vue 3 no renderer
3. backend remoto stateless em FastAPI
4. Supabase como camada de persistencia

### 15.5 Consequencias positivas

1. UX desktop mais forte
2. melhor integracao com arquivos locais
3. backend escalavel e centralizado
4. persistencia operacional simplificada

### 15.6 Consequencias negativas

1. maior complexidade de distribuicao
2. necessidade de manter shell desktop
3. mais disciplina arquitetural para nao inflar o cliente

### 15.7 Alternativas descartadas

1. manter web hospedada como arquitetura principal
2. adotar Blazor WASM no frontend
3. embutir backend local como estrategia principal

---

## 16. Recomendacao Final

A V2 deve ser tratada como a arquitetura-alvo preferencial do projeto. A V1 permanece como referencia historica, mas a implementacao futura deve assumir:

1. Electron como shell desktop
2. Vue como camada de interface
3. FastAPI como backend remoto stateless
4. Supabase como persistencia de servidor

