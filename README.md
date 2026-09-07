# 🚀 Sistema de Monitoramento e Agregação de Vagas
### Pelotas & Rio Grande - RS

Sistema automatizado para monitorar, agregar, filtrar e gerenciar vagas de emprego nas cidades de **Rio Grande** e **Pelotas** (RS) e oportunidades remotas nas áreas de:
- ⚡ **Elétrica, Eletrônica & Instrumentação**: Eletricista (Industrial/Predial/Força e Controle), Eletroinstrumentista, Técnico em Eletrônica, Técnico em Eletrotécnica, Automação.
- 💻 **Tecnologia & Dados (Júnior)**: Desenvolvedor/Programador Júnior (Frontend, Backend, Fullstack, Python, etc.), Analista de Dados Júnior / BI.
- 📊 **Gestão & Projetos**: Analista de Projetos, Assistente de Projetos, PMO.

---

## 🌟 Fontes de Coleta Integradas

1. **LinkedIn (Vagas Públicas & Recentes)**:
   - Captura em tempo real de oportunidades publicadas no LinkedIn para Pelotas e Rio Grande (Equatorial, Sicredi, Senior Sistemas, Tholz, Jobbol, etc.).
2. **Trabalha Brasil / SINE**:
   - Varredura de vagas industriais, técnicas e locais de Pelotas e Rio Grande.
3. **Gupy API**:
   - Captura direta de vagas de grandes empresas com atuação local ou vagas remotas.
4. **Catho**:
   - Vagas técnicas e administrativas publicadas no portal.

> Todas as vagas exibidas vêm de varredura real nos portais acima. O sistema não
> cria oportunidades próprias: se uma vaga aparece no feed, ela foi encontrada
> num portal e o link leva à publicação original.

---

## 🛠️ Como Executar

### Opção 1: Execução Rápida no Windows (1 Clique)
Basta dar dois cliques no arquivo:
```cmd
start.bat
```
O script iniciará o servidor e abrirá automaticamente o navegador em `http://localhost:8000`.

---

### Opção 2: Linha de Comando (Terminal / PowerShell)

```bash
python server.py 8000
```
Acesse: [http://localhost:8000](http://localhost:8000)

> O servidor roda sobre a biblioteca padrão do Python. As dependências de
> `requirements.txt` (beautifulsoup4, pyyaml, httpx) são usadas apenas pelos
> coletores e pelo alerta do Telegram.

---

## ☁️ Sincronização entre celular e computador (Opcional)

O app funciona sem conta: tudo fica salvo no navegador do aparelho. Para
sincronizar status e anotações entre celular e computador é preciso entrar com
e-mail — suas anotações são privadas e o banco precisa saber de quem elas são.

**Configuração inicial do banco (uma vez):**

1. No painel do Supabase, abra **SQL Editor**.
2. Cole e execute `supabase/migrations/0001_auth_rls.sql`.
3. Abra o app, vá em **Nuvem & Alertas**, informe seu e-mail e clique em
   **Receber link de acesso**.
4. Depois do primeiro login, volte ao SQL Editor e rode o bloco do **passo 5**
   do arquivo (trocando o e-mail) para adotar os registros antigos, gravados
   quando a tabela ainda não tinha dono.

Sem esse SQL aplicado, o login funciona mas nenhuma linha é lida ou gravada: o
RLS bloqueia tudo que não tem dono definido.

**Como o conflito é resolvido:** cada alteração carrega a hora em que foi feita.
Quando celular e computador discordam sobre a mesma vaga, vence a alteração mais
recente. Alterações feitas offline entram numa fila local e sobem no próximo
login ou sincronização — o contador aparece no cabeçalho.

---

## 🧪 Testes

```bash
python -m unittest discover -s tests -v
```

Cobre a lógica pura mais sensível a regressão: resolução de datas relativas
(`backend/app/core/dates.py`), escape do `LIKE` na deduplicação
(`backend/app/database/db.py`) e a extração de `<title>`/`<h1>` que o
verificador de links usa para decidir se uma vaga encerrou
(`backend/app/services/verifier.py`). Roda automaticamente em cada push/PR
via `.github/workflows/tests.yml`.

---

## 📱 Configuração de Alertas no Telegram (Opcional)

1. Crie um bot no Telegram com o [@BotFather](https://t.me/botfather) e copie o **Bot Token**.
2. Obtenha seu **Chat ID** conversando com o [@userinfobot](https://t.me/userinfobot).
3. No painel web, clique no ícone de **Engrenagem ⚙️**, insira o Token e Chat ID e clique em **Testar Envio**.
