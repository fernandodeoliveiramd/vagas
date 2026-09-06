# Levantamento do repositório — Vagas Pelotas & Rio Grande (RS)

> Análise gerada pelo Claude Code em 2026-09-04.

## 1. Propósito e natureza do projeto

Ferramenta pessoal do Fernando para caçar vagas de emprego em Pelotas/Rio Grande (RS) — nas áreas de elétrica/automação industrial, tecnologia júnior e gestão de projetos — com pipeline estilo Kanban para acompanhar candidaturas. Não é um produto para terceiros: tem currículos pessoais, carta de apresentação e é hospedado como site estático pessoal no GitHub Pages (`.nojekyll` na raiz confirma isso).

## 2. Três formas de rodar, um único frontend

- **`backend/main.py`** — FastAPI "completo", com scheduler automático a cada 3h.
- **`server.py`** — servidor `http.server` puro que reimplementa manualmente as mesmas rotas (`/api/jobs`, `/api/stats`, `/api/config`, `/api/jobs/scrape`, `/api/test-telegram`, PATCH de status/notas, DELETE) — é o que `start.bat` usa para o "clique único" no Windows, evitando dependência do FastAPI instalado.
- **GitHub Pages estático** — `export_static.py` roda via Actions e grava `data/jobs.json`/`data/stats.json`; o frontend detecta ausência de API (`fetch('./api/...')` falha) e cai automaticamente para os JSONs estáticos (`index.html:1015-1023, 1040-1049`).

O HTML da UI (1673 linhas, Tailwind via CDN + Material Symbols) é **idêntico** em `index.html` e `frontend/index.html` — mantidos manualmente sincronizados.

## 3. Camada de dados (`backend/app/database/db.py`)

- SQLite com WAL mode, tabelas `jobs` e `scrape_logs`.
- **Deduplicação em 3 camadas** (`db.py:96-122`): por `external_id` → por URL normalizada (remove `?`, `#`, barra final, força `https`) → por hash SHA-256 de `título|empresa|localização` (cai para incluir a URL no hash quando a empresa é "confidencial", para não fundir vagas anônimas diferentes).
- `sync_jobs_from_json()` é a peça-chave que evita "vagas fantasma reaparecendo como novas" no Actions: a cada execução do workflow (ambiente efêmero, banco recriado do zero), o script repovoa o SQLite a partir do `data/jobs.json` do commit anterior antes de rodar os scrapers, preservando `id`, `created_at`, `status`, `notes`.

## 4. Motor de classificação (`backend/app/core/config.py`)

`AppConfig.match_job()`: normaliza texto (remove acentos/pontuação), aplica keywords negativas (bloqueia "sênior", "coordenador" etc., a menos que o título também contenha termos júnior), depois pontua por categoria/cargo — match no **título** vale 65+ pontos, match só na descrição precisa de ≥2 keywords para valer 30+. Detecta cidade e modalidade (presencial/híbrido/remoto) por regras de texto simples. Config sobrescrita por `config/keywords.yaml` e `config/locations.yaml`, com fallback hardcoded idêntico embutido no próprio `config.py` (redundância proposital para funcionar sem os YAMLs).

## 5. Scrapers — 4 ativos, 2 órfãos

Coordenados por `manager.py` via `asyncio.gather` (paralelo):

- **LinkedIn** — usa o endpoint público `jobs-guest/jobs/api/seeMoreJobPostings` (sem login), filtra por `f_TPR=r2592000` (últimos 30 dias), 23 combinações cargo×cidade por execução.
- **Trabalha Brasil** — scraping de HTML puro via regex em hrefs (`vagas-de-emprego-em-{cidade}/{cargo}`), 20 combinações.
- **Gupy** — API JSON pública (`portal.gupy.io/api/v1/jobs`), filtra por cidade/remoto no título e local.
- **Polo Regional** (`local_feed.py`) — **dados 100% hardcoded**, 4 vagas fixas (Wilson Sons, Sagres, Sicredi, Equatorial) — não é scraping real, é uma lista estática de "sempre considerar essas oportunidades". Isso explica por que aparecem sempre nas estatísticas.
- **InfoJobs** e **Vagas.com** (`infojobs.py`, `vagas_com.py`) — implementados com `httpx` + seletores CSS, mas **não registrados** em `ScraperManager.scrapers` — código morto, possivelmente porque os seletores pararam de funcionar ou foram abandonados em favor dos outros.

Todos usam `ssl.CERT_NONE`/`check_hostname = False` para contornar problemas de certificado — aceitável para scraping de leitura, mas desativa validação TLS (não valida a identidade do servidor).

## 6. Verificação de vagas expiradas (`verifier.py`)

Após cada scrape, `verify_and_clean_all_jobs()` visita cada URL salva e:

- Remove se HTTP 404/410, domínio inexistente, ou se o HTML contém uma de ~19 frases-gatilho ("vaga encerrada", "no longer accepting applications" etc.)
- Mantém como ativa em caso de 429/403 (rate-limit/Cloudflare) — assume que a vaga ainda existe.

## 7. Notificações e agendamento

- `telegram.py` — bot simples via Bot API, token/chat ID configuráveis por variável de ambiente **ou** inseridos na UI (aba "Nuvem & Alertas") e testados ao vivo.
- `scheduler.py` — `apscheduler` roda `scraper_manager.run_all()` a cada 3h (só no modo FastAPI local; o GitHub Actions cuida da cadência de 4h em 4h quando hospedado no Pages).

## 8. Frontend (SPA vanilla JS em `index.html`)

- Layout "Split View" (lista + inspetor de detalhes) com toggle para visão em tabela, filtros por cidade/modalidade/status/categoria, busca com debounce de 200ms.
- Estado do usuário (status, notas, "visualizado") persiste em **três camadas**: `localStorage` (imediato) → PATCH para a API local (se disponível) → **Supabase** (Postgres gerenciado, sincronização em tempo real via canal `postgres_changes` na tabela `user_job_interactions`, chave por `job_key` = `external_id` ou hash de dedup).
- Import/export manual de backup em JSON e exportação de CSV.
- `escapeHtml()` é usado consistentemente ao renderizar campos de vaga — sem XSS óbvio nos pontos revisados.
- **Chave anon do Supabase hardcoded no HTML** (`index.html:689`) — padrão para apps Supabase client-side (a chave anon é pública por design), mas a segurança real depende inteiramente das políticas de RLS na tabela `user_job_interactions`; não foi possível verificar essas políticas a partir do repositório.

## 9. Automação CI (`.github/workflows/scrape.yml`)

Cron a cada 4h + em todo push na `main`, roda `export_static.py`, comita `data/jobs.json`/`stats.json` com `[skip ci]` (evita loop infinito de disparo). Explica a cauda de commits "chore: atualizar vagas..." no histórico.

## 10. Artefatos de design (Google Stitch)

`fetch_stitch.js` — script Node que autentica via `gcloud`, baixa 6 telas do Google Stitch (ferramenta de design da Google) usando o MCP `@_davideast/stitch-mcp`, salva como `stitch_screen_N.html/json` e `stitch_summary.json`. `payload.json` é só o parâmetro temporário da última chamada (`projectId`/`screenId`). Pelo commit `241b00b` ("integrar novo frontend moderno projetado no Google Stitch"), essas telas foram a base visual do `index.html` atual — os arquivos `stitch_screen_*` parecem ser rascunhos/histórico de design, prováveis candidatos a limpeza se não forem mais referenciados.

## 11. Scripts de teste — não são testes automatizados

`test_gupy.py`, `test_scraper.py`, `test_sources.py` são scripts exploratórios ad-hoc (sem asserts, sem framework de teste), usados para depurar scraping manualmente — e por isso corretamente ignorados no git (`.gitignore:11-13`). `verify_jobs.py` na raiz é uma versão standalone/duplicada de `verifier.py`, rodável direto contra `data/jobs.json` sem precisar do banco — também não versionado como teste formal, mas este **está** no git (ao contrário dos `test_*.py`).

## 12. Pontos de atenção consolidados

1. **Duplicação tripla de lógica de API** entre `server.py`, `backend/app/api/routes.py`, e indiretamente a UI que tenta ambos — qualquer mudança de regra de negócio (ex: novo campo, nova validação) precisa ser replicada em pelo menos dois lugares.
2. **`verify_jobs.py`** duplica quase byte-a-byte a lógica de `verifier.py` — poderia ser substituído por uma chamada ao módulo real.
3. **Scrapers órfãos** (`infojobs.py`, `vagas_com.py`) — código morto ou pendente de reativação.
4. **`index.html` / `frontend/index.html` duplicados** — risco de divergência silenciosa.
5. **TLS desabilitado** em todos os scrapers e no verifier (`CERT_NONE`) — funcional mas reduz a garantia de estar de fato falando com o domínio esperado.
6. **`local_feed.py`** não faz scraping real — são 4 vagas fixas: bom saber para não interpretar as estatísticas como 100% "vagas descobertas dinamicamente".
7. Sem testes automatizados formais (nenhum `pytest`/`unittest` real) — a validação de scraping é toda manual/exploratória.

## Estado dos dados no momento da análise

- 39 vagas ativas no banco (`data/jobs.db` + `data/jobs.json`), todas com status "nova"
- Distribuição por categoria: 34 industrial/elétrica, 3 tecnologia júnior, 2 gestão de projetos
- Distribuição por cidade: 23 Rio Grande, 14 Pelotas, 2 remoto
- Fontes: Trabalha Brasil (29), LinkedIn (8), Sicredi e Wilson Sons (1 cada)
