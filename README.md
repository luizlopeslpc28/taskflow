# TaskFlow

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.x-000000?style=flat&logo=flask&logoColor=white)
![Supabase](https://img.shields.io/badge/Supabase-PostgreSQL-3FCF8E?style=flat&logo=supabase&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-yellow?style=flat)

**TaskFlow** é um gerenciador de tarefas com workspaces e quadro Kanban. Cada usuário tem sua própria conta, seus ambientes de trabalho e suas tarefas — com autenticação e dados isolados via Supabase.

---

## Índice

- [Sobre o projeto](#sobre-o-projeto)
- [Funcionalidades](#funcionalidades)
- [Demonstração](#demonstração)
- [Stack](#stack)
- [Arquitetura](#arquitetura)
- [Segurança](#segurança)
- [Estrutura do repositório](#estrutura-do-repositório)
- [Pré-requisitos](#pré-requisitos)
- [Instalação e execução](#instalação-e-execução)
- [Variáveis de ambiente](#variáveis-de-ambiente)
- [Banco de dados (Supabase)](#banco-de-dados-supabase)
- [API](#api)
- [Scripts úteis](#scripts-úteis)
- [Deploy (produção)](#deploy-produção)
- [Decisões técnicas](#decisões-técnicas)
- [Roadmap](#roadmap)
- [Licença](#licença)
- [Autor](#autor)

---

## Sobre o projeto

O TaskFlow nasceu como exercício full stack: unir um backend em Python (Flask), autenticação e PostgreSQL gerenciados (Supabase) e uma interface web simples, sem framework JS pesado.

O foco foi entregar um fluxo real de produto:

1. Cadastro e login  
2. Criação de workspaces  
3. Tarefas organizadas em Kanban  
4. Isolamento de dados por usuário  
5. Boas práticas mínimas de segurança para uso real  

Ideal para portfólio de **backend Python**, **full stack júnior** ou estudos de **Auth + RLS**.

---

## Funcionalidades

| Área | Detalhes |
|------|----------|
| **Contas** | Cadastro e login com e-mail e senha (Supabase Auth) |
| **Workspaces** | Criar, editar e excluir ambientes de trabalho |
| **Tarefas** | Criar, editar, excluir e mudar status |
| **Kanban** | Colunas *Pendente*, *Em produção* e *Finalizado* |
| **Drag and drop** | Arrastar cards entre colunas para atualizar o status |
| **Tema** | Modo claro e escuro |
| **Sessão** | Logout, proteção de rotas e redirecionamento se não autenticado |

---

## Demonstração

> Substitua pelos seus prints ou pela URL da demo quando publicar.

- **Repositório:** `https://github.com/luizlopeslpc28/taskflow.git`
- **Demo online (opcional):** `https://sua-url-de-deploy`

Fluxo sugerido nas capturas:

1. Tela de login / cadastro  
2. Lista de workspaces na sidebar  
3. Quadro Kanban com tarefas  
4. Tema escuro  

---

## Stack

| Camada | Tecnologia |
|--------|------------|
| Backend | Python 3, Flask |
| Auth | Supabase Auth |
| Banco | PostgreSQL (Supabase) + Row Level Security |
| Frontend | HTML5, CSS3, JavaScript (vanilla) |
| Fonte / UI | Manrope, design flat, tema claro/escuro |
| Config | python-dotenv |
| Rate limit | Flask-Limiter |

---

## Arquitetura

```
┌─────────────┐     HTTPS/JSON      ┌─────────────┐     JWT + REST     ┌──────────────────┐
│  Navegador  │ ◄─────────────────► │    Flask    │ ◄────────────────► │    Supabase      │
│  (HTML/JS)  │                     │  (API + UI) │                    │ Auth + Postgres  │
└─────────────┘                     └─────────────┘                    └──────────────────┘
```

- O frontend chama apenas a API do Flask (`/api/...`).  
- O Flask autentica com Supabase Auth e guarda a sessão (cookie HttpOnly).  
- Operações em `workspaces` e `tasks` usam o **JWT do usuário** (chave `anon` + sessão).  
- O **RLS** no Postgres garante que cada usuário só acessa as próprias linhas.

---

## Segurança

- Senhas tratadas pelo Supabase Auth (não armazenadas no Flask)  
- Isolamento por `user_id` + **RLS** no PostgreSQL  
- Queries de dados **sem** `service_role` (evita bypass do RLS)  
- Rate limit em login e cadastro  
- Senha mínima: 8 caracteres, com letras e números  
- Cookies: `HttpOnly`, `SameSite=Lax`; `Secure` quando `FLASK_ENV=production`  
- Headers: CSP, `X-Frame-Options`, `X-Content-Type-Options`, HSTS em produção  
- Arquivo `.env` fora do Git (veja `.gitignore`)  

---

## Estrutura do repositório

```text
flask_app/
├── app.py                  # Aplicação Flask (rotas, auth, API)
├── requirements.txt        # Dependências Python
├── supabase_schema.sql     # Tabelas + índices + políticas RLS
├── .env.example            # Modelo de variáveis (sem segredos)
├── .gitignore
├── README.md
├── SETUP_SUPABASE.md       # Guia detalhado do Supabase
├── templates/
│   ├── index.html          # App principal (Kanban)
│   ├── login.html
│   └── register.html
└── static/
    ├── css/
    │   ├── styles.css
    │   └── auth.css
    └── js/
        └── app.js          # Frontend (API, Kanban, tema)
```

---

## Pré-requisitos

- Python 3.10 ou superior  
- Conta no [Supabase](https://supabase.com)  
- Git (opcional, para clonar)  

---

## Instalação e execução

### 1. Clonar o repositório

```bash
git clone https://github.com/luizlopeslpc28/taskflow.git
cd SEU_REPO
```

### 2. (Recomendado) Ambiente virtual

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux / macOS
source .venv/bin/activate
```

### 3. Instalar dependências

```bash
python -m pip install -r requirements.txt
```

### 4. Configurar Supabase

1. Crie um projeto no Supabase.  
2. Abra **SQL Editor**, cole o conteúdo de `supabase_schema.sql` e execute.  
3. Em **Project Settings → API**, copie:
   - **Project URL**
   - chave **anon public**

### 5. Arquivo `.env`

```bash
# Windows
copy .env.example .env

# Linux / macOS
cp .env.example .env
```

Edite o `.env` (veja a seção [Variáveis de ambiente](#variáveis-de-ambiente)).

Gere a secret key:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 6. Subir a aplicação

```bash
python app.py
```

Acesse: **http://127.0.0.1:5000**

- Cadastro: `/register`  
- Login: `/login`  
- App: `/`  

---

## Variáveis de ambiente

| Variável | Obrigatória | Descrição |
|----------|-------------|-----------|
| `SUPABASE_URL` | Sim | URL do projeto Supabase |
| `SUPABASE_ANON_KEY` | Sim | Chave pública `anon` |
| `FLASK_SECRET_KEY` | Sim (prod) | Segredo das sessões Flask |
| `FLASK_ENV` | Não | `development` ou `production` (padrão: production) |
| `PORT` | Não | Porta HTTP (padrão: 5000) |

**Não** versionar o arquivo `.env`. Use apenas o `.env.example` no Git.

---

## Banco de dados (Supabase)

Tabelas principais:

- **workspaces** — `id`, `user_id`, `name`, timestamps  
- **tasks** — `id`, `workspace_id`, `user_id`, `title`, `description`, `status`, timestamps  

`status` permitido: `pendente` | `em_producao` | `finalizado`

Políticas RLS: o usuário autenticado só faz SELECT/INSERT/UPDATE/DELETE nas linhas em que `user_id = auth.uid()`.

Detalhes extras: `SETUP_SUPABASE.md`.

---

## API

Base: mesmo host da aplicação. Rotas de dados exigem sessão autenticada.

### Auth

| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/api/auth/register` | Cadastro |
| POST | `/api/auth/login` | Login |
| POST | `/api/auth/logout` | Logout |
| GET | `/api/auth/me` | Usuário da sessão |

### Workspaces

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/workspaces` | Listar |
| POST | `/api/workspaces` | Criar |
| PUT | `/api/workspaces/<id>` | Atualizar |
| DELETE | `/api/workspaces/<id>` | Excluir |

### Tarefas

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/workspaces/<id>/tasks` | Listar do workspace |
| POST | `/api/workspaces/<id>/tasks` | Criar |
| PUT | `/api/tasks/<id>` | Atualizar |
| PATCH | `/api/tasks/<id>/status` | Só o status (Kanban) |
| DELETE | `/api/tasks/<id>` | Excluir |

---

## Scripts úteis

```bash
# Dependências
python -m pip install -r requirements.txt

# Secret key
python -c "import secrets; print(secrets.token_hex(32))"

# Rodar
python app.py
```

---

## Deploy (produção)

Checklist mínimo:

1. `FLASK_ENV=production`  
2. HTTPS obrigatório (cookie `Secure`)  
3. Confirmação de e-mail ativada no Supabase  
4. Servidor WSGI (ex.: Gunicorn) atrás de Nginx/Caddy ou PaaS (Render, Railway, etc.)  
5. Variáveis de ambiente configuradas no painel do host — nunca no código  

Exemplo com Gunicorn:

```bash
pip install gunicorn
gunicorn -w 2 -b 0.0.0.0:5000 app:app
```

---

## Decisões técnicas

| Decisão | Motivo |
|---------|--------|
| Flask + templates/static | Simplicidade e controle total do front |
| Supabase Auth | Auth maduro sem reinventar hash/sessão |
| JWT do usuário + RLS | Isolamento no banco, não só no Python |
| Sem `service_role` nas queries | Evita contornar o RLS por acidente |
| Kanban em JS puro | Menos dependências, fácil de entender no portfólio |

---

## Roadmap

Ideias para evolução:

- [ ] Deploy público com URL de demo  
- [ ] Testes automatizados (pytest)  
- [ ] CI no GitHub Actions  
- [ ] Recuperação de senha  
- [ ] OAuth (Google)  
- [ ] Prazos e prioridades nas tarefas  
- [ ] Compartilhamento de workspace entre usuários  

---

## Licença

MIT — uso livre para estudo, portfólio e adaptações.

---

## Autor

**Luiz** — desenvolvedor em formação / portfólio.

- GitHub: [https://github.com/SEU_USUARIO](https://github.com/SEU_USUARIO)  
- LinkedIn: *(opcional)*  

> Substitua `SEU_USUARIO`, links e a seção Autor pelos seus dados reais.

---

Feito com Flask, Supabase e foco em um fluxo completo de produto.