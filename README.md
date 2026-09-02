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
4. **Polo Regional (Pelotas & Rio Grande)**:
   - Oportunidades do Polo Industrial/Portuário de Rio Grande (Wilson Sons, Tecon, Sagres, EBR) e Pelotas Parque Tecnológico (Lifemed, Cigam, Startups).

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

---

## 📱 Configuração de Alertas no Telegram (Opcional)

1. Crie um bot no Telegram com o [@BotFather](https://t.me/botfather) e copie o **Bot Token**.
2. Obtenha seu **Chat ID** conversando com o [@userinfobot](https://t.me/userinfobot).
3. No painel web, clique no ícone de **Engrenagem ⚙️**, insira o Token e Chat ID e clique em **Testar Envio**.
