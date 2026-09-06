-- =====================================================================
-- Vagas RS - autenticacao e Row Level Security
--
-- Estado anterior: a tabela user_job_interactions era lida e escrita
-- pela chave anon, sem RLS. Qualquer pessoa com a URL da pagina publica
-- (ou com o repositorio, onde a chave esta no index.html) conseguia ler
-- as anotacoes privadas e sobrescrever o pipeline inteiro.
--
-- Depois desta migracao cada linha pertence a um usuario autenticado e
-- so ele enxerga as proprias linhas.
--
-- Como aplicar: Supabase -> SQL Editor -> cole este arquivo -> Run.
-- E idempotente: pode rodar mais de uma vez sem quebrar.
--
-- ORDEM IMPORTA: rode este arquivo (passos 1-4 e 7), DEPOIS faca login
-- pelo menos uma vez no app, DEPOIS rode o passo 5. Se o passo 5 nao
-- rodar antes do primeiro uso autenticado, qualquer upsert em um
-- job_key que ja tinha linha orfa (user_id nulo) falha com
-- "duplicate key value violates unique constraint
-- user_job_interactions_pkey" - a chave primaria da tabela e job_key
-- sozinho, entao o upsert por (user_id, job_key) tenta inserir uma
-- segunda linha para o mesmo job_key em vez de atualizar a orfa.
-- (Aconteceu exatamente isso na aplicacao real desta migracao.)
-- =====================================================================

-- ---------------------------------------------------------------------
-- 1. Coluna de dono
--
-- Nullable neste primeiro momento para nao invalidar as linhas que ja
-- existem. O passo 5 adota essas linhas orfas e o passo 6 fecha a coluna.
-- ---------------------------------------------------------------------
alter table public.user_job_interactions
  add column if not exists user_id uuid references auth.users (id) on delete cascade;

-- O cliente nunca envia user_id: o banco carimba a partir do token JWT.
-- Isso remove a possibilidade de um cliente gravar linha em nome de outro.
alter table public.user_job_interactions
  alter column user_id set default auth.uid();

-- ---------------------------------------------------------------------
-- 2. Chave de conflito do upsert
--
-- A tabela ja tinha job_key como PRIMARY KEY (user_job_interactions_pkey).
-- Isso continua valendo aqui de proposito: este e um app de um usuario
-- so (varios aparelhos, uma pessoa), entao job_key globalmente unico
-- nunca chega a colidir de verdade. O indice abaixo existe apenas para
-- o app conseguir fazer upsert(onConflict: 'user_id,job_key') sem
-- precisar remodelar a chave primaria.
--
-- (Uma versao anterior deste arquivo tentava "drop constraint
-- user_job_interactions_job_key_key" - nome que nunca existiu; o
-- "if exists" so evitou erro, nao fez nada. Corrigido aqui.)
-- ---------------------------------------------------------------------
create unique index if not exists user_job_interactions_user_job_key_idx
  on public.user_job_interactions (user_id, job_key);

create index if not exists user_job_interactions_user_id_idx
  on public.user_job_interactions (user_id);

-- ---------------------------------------------------------------------
-- 3. updated_at
--
-- O cliente envia o proprio updated_at porque e ele quem resolve
-- conflitos entre aparelhos (last-write-wins por relogio do cliente).
-- O default aqui e so uma rede de seguranca para escritas manuais.
-- ---------------------------------------------------------------------
alter table public.user_job_interactions
  alter column updated_at set default now();

-- ---------------------------------------------------------------------
-- 4. Row Level Security
--
-- ATENCAO: sem "enable row level security" as policies abaixo nao valem
-- nada - elas ficam definidas e simplesmente nao sao aplicadas.
-- ---------------------------------------------------------------------
alter table public.user_job_interactions enable row level security;

-- "force" faz o RLS valer inclusive para o dono da tabela. Sem isso, uma
-- conexao que use o papel proprietario ignora as policies em silencio.
alter table public.user_job_interactions force row level security;

-- "Acesso publico frontend" e o nome real de uma policy que ja existia
-- nesta tabela antes desta migracao: PERMISSIVE, ALL, para o papel
-- "public", com qual=true e with_check=true. Policies permissivas se
-- combinam por OR, entao ela sozinha anulava qualquer restricao das
-- policies abaixo para todo usuario autenticado (nao so para anon).
-- So foi encontrada rodando "select * from pg_policies" contra o banco
-- de producao - nao tinha como prever o nome sem introspeccao.
drop policy if exists "Acesso público frontend"    on public.user_job_interactions;
drop policy if exists "anon_full_access"           on public.user_job_interactions;
drop policy if exists "Enable read access for all" on public.user_job_interactions;
drop policy if exists "own_rows_select"            on public.user_job_interactions;
drop policy if exists "own_rows_insert"            on public.user_job_interactions;
drop policy if exists "own_rows_update"            on public.user_job_interactions;
drop policy if exists "own_rows_delete"            on public.user_job_interactions;

-- Quatro policies separadas em vez de uma "for all": deixa explicito o
-- que cada verbo pode fazer e evita o buraco classico do update, em que
-- o USING permite ler a linha e a ausencia de WITH CHECK permite
-- reatribui-la a outro dono.
create policy "own_rows_select" on public.user_job_interactions
  for select to authenticated
  using (user_id = auth.uid());

create policy "own_rows_insert" on public.user_job_interactions
  for insert to authenticated
  with check (user_id = auth.uid());

create policy "own_rows_update" on public.user_job_interactions
  for update to authenticated
  using (user_id = auth.uid())          -- quais linhas posso alterar
  with check (user_id = auth.uid());    -- em quem elas podem virar depois

create policy "own_rows_delete" on public.user_job_interactions
  for delete to authenticated
  using (user_id = auth.uid());

-- O papel anon perde qualquer acesso. Sem nenhuma policy para ele, todo
-- select/insert vindo de sessao nao autenticada volta vazio ou falha.
revoke all on public.user_job_interactions from anon;
grant select, insert, update, delete on public.user_job_interactions to authenticated;

-- ---------------------------------------------------------------------
-- 5. Adocao das linhas que ja existiam
--
-- Rode este bloco DEPOIS de fazer login pela primeira vez no app, e
-- troque o e-mail abaixo pelo seu. Ele atribui a voce todas as linhas
-- gravadas na epoca em que a tabela era aberta.
--
-- Sem isso, seu historico de status e anotacoes continua no banco mas
-- fica invisivel - o RLS filtra tudo que tem user_id nulo.
--
-- Ja executado em producao em 2026-09-06 para fernandodeoliveira.md@gmail.com:
-- 34 linhas orfas adotadas. O passo 6 tambem ja foi aplicado (user_id
-- e NOT NULL desde entao). Mantido aqui comentado como referencia para
-- quem recriar este banco do zero.
-- ---------------------------------------------------------------------
-- update public.user_job_interactions
--    set user_id = (select id from auth.users where email = 'seu-email@exemplo.com')
--  where user_id is null;

-- ---------------------------------------------------------------------
-- 6. Fechamento (opcional, recomendado) - JA APLICADO EM PRODUCAO
--
-- Depois de conferir que o passo 5 nao deixou nenhuma linha orfa, torne
-- a coluna obrigatoria. A partir daqui e impossivel gravar linha sem dono.
--
--   select count(*) from public.user_job_interactions where user_id is null;
--   -- se retornar 0:
--   alter table public.user_job_interactions alter column user_id set not null;
-- ---------------------------------------------------------------------

-- ---------------------------------------------------------------------
-- 7. Realtime
--
-- O Realtime respeita RLS: cada aparelho so recebe eventos das proprias
-- linhas, desde que a publicacao inclua a tabela.
-- ---------------------------------------------------------------------
do $$
begin
  alter publication supabase_realtime add table public.user_job_interactions;
exception
  when duplicate_object then null;  -- ja estava na publicacao
end $$;

-- Faz o payload do Realtime trazer a linha inteira no UPDATE, e nao so
-- as colunas da chave primaria - o cliente precisa de status/notes/viewed.
alter table public.user_job_interactions replica identity full;

-- =====================================================================
-- Verificacao
-- =====================================================================
-- select relrowsecurity, relforcerowsecurity
--   from pg_class where relname = 'user_job_interactions';
--   -- as duas colunas devem ser true
--
-- select policyname, cmd, roles from pg_policies
--  where tablename = 'user_job_interactions';
--   -- devem aparecer as 4 policies, todas para {authenticated}
