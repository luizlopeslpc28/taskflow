# TaskFlow — Setup seguro (produção)

## Arquitetura de segurança

- **Auth**: Supabase Auth (hash de senha no Supabase)
- **Dados**: PostgreSQL + **RLS** (Row Level Security)
- **API**: Flask usa o **JWT do usuário** (anon key + `set_session`)
  - O Postgres só devolve linhas onde `auth.uid() = user_id`
  - **Não** usamos `service_role` nas queries de dados
- **Rate limit** em login/cadastro
- **Senha**: mínimo 8 caracteres, letras e números
- **Cookies**: HttpOnly, SameSite=Lax, Secure em produção
- **Headers**: CSP, X-Frame-Options, HSTS (prod), etc.

## 1. Projeto Supabase

1. https://supabase.com/dashboard → criar projeto
2. **Project Settings → API**:
   - `SUPABASE_URL`
   - `anon` `public` → `SUPABASE_ANON_KEY`

## 2. SQL (tabelas + RLS)

SQL Editor → cole e execute `supabase_schema.sql`.

## 3. Auth e-mail

**Authentication → Providers → Email**

- Em **produção**: mantenha **Confirm email** ativado
- Em **dev local**: pode desativar para testar mais rápido

## 4. Arquivo `.env`

```powershell
copy .env.example .env
```

Preencha URL, anon key e:

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

Para desenvolvimento:

```
FLASK_ENV=development
```

Para produção (HTTPS):

```
FLASK_ENV=production
```

## 5. Rodar

```powershell
python -m pip install -r requirements.txt
python app.py
```

http://127.0.0.1:5000

## Checklist produção

- [ ] HTTPS (Nginx, Caddy, Cloudflare Tunnel, etc.)
- [ ] `FLASK_ENV=production`
- [ ] `FLASK_SECRET_KEY` forte e único
- [ ] `.env` fora do Git (adicione ao `.gitignore`)
- [ ] Confirm email ativado no Supabase
- [ ] SQL/RLS aplicado
- [ ] Não expor `service_role` em lugar nenhum deste app
- [ ] Backup do projeto Supabase habilitado (plano pago ou export)

## O que o RLS garante

Mesmo se houver bug no Flask, o Postgres **recusa** ler/escrever linhas de outro usuário quando a requisição vai com o JWT correto. Isso é a defesa em profundidade.
