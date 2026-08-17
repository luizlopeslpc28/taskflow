#!/usr/bin/env python3
"""
TaskFlow — Flask + Supabase (produção)
Auth via JWT do usuário + RLS no Postgres (sem service_role nas queries de dados).
Rate limit, headers de segurança, senha forte, cookies seguros.
"""

from __future__ import annotations

import os
import re
import uuid
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path

from dotenv import load_dotenv
from flask import (
    Flask,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from supabase import Client, create_client
from supabase_auth.errors import AuthApiError

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
APP_DIR = Path(__file__).resolve().parent
load_dotenv(APP_DIR / ".env")

SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "").strip()
FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "").strip()
FLASK_ENV = os.getenv("FLASK_ENV", "production").strip().lower()
IS_PROD = FLASK_ENV == "production"

STATUSES = ("pendente", "em_producao", "finalizado")
EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
PASSWORD_MIN = 8

app = Flask(__name__)
app.secret_key = FLASK_SECRET_KEY or os.urandom(32).hex()
app.config["JSON_AS_ASCII"] = False
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = IS_PROD  # HTTPS obrigatório em produção
app.config["PERMANENT_SESSION_LIFETIME"] = 60 * 60 * 24 * 7  # 7 dias
app.config["MAX_CONTENT_LENGTH"] = 64 * 1024  # 64 KB

limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=["200 per hour", "40 per minute"],
    storage_uri="memory://",
)


def uid() -> str:
    return uuid.uuid4().hex[:12]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def check_config() -> list[str]:
    missing = []
    if not SUPABASE_URL:
        missing.append("SUPABASE_URL")
    if not SUPABASE_ANON_KEY:
        missing.append("SUPABASE_ANON_KEY")
    if not FLASK_SECRET_KEY and IS_PROD:
        missing.append("FLASK_SECRET_KEY")
    return missing


def public_error(message: str, status: int = 400):
    """Mensagens genéricas em produção; detalhe só em development."""
    if IS_PROD and status >= 500:
        return jsonify({"error": "Erro interno. Tente novamente."}), status
    return jsonify({"error": message}), status


# ---------------------------------------------------------------------------
# Supabase clients — sempre com JWT do usuário para RLS valer
# ---------------------------------------------------------------------------
def get_anon_client() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_ANON_KEY)


def get_user_client() -> Client | None:
    """
    Client autenticado com o access_token da sessão.
    Todas as operações em tables passam pelo RLS (auth.uid()).
    """
    access = session.get("access_token")
    refresh = session.get("refresh_token")
    if not access:
        return None
    client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    try:
        client.auth.set_session(access, refresh or "")
    except Exception:
        # Tenta refresh se houver refresh_token
        if refresh:
            try:
                res = client.auth.refresh_session(refresh)
                if res.session:
                    session["access_token"] = res.session.access_token
                    if res.session.refresh_token:
                        session["refresh_token"] = res.session.refresh_token
                    session.modified = True
                    client.auth.set_session(
                        res.session.access_token,
                        res.session.refresh_token or "",
                    )
                else:
                    return None
            except Exception:
                return None
        else:
            return None
    return client


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("user_id") or not session.get("access_token"):
            if request.path.startswith("/api/"):
                return jsonify({"error": "Não autenticado"}), 401
            return redirect(url_for("login_page"))
        return f(*args, **kwargs)

    return decorated


def current_user_id() -> str | None:
    return session.get("user_id")


def validate_email(email: str) -> str | None:
    email = (email or "").strip().lower()
    if not email or len(email) > 254 or not EMAIL_RE.match(email):
        return None
    return email


def validate_password(password: str) -> str | None:
    """Retorna mensagem de erro ou None se ok."""
    if not password or len(password) < PASSWORD_MIN:
        return f"A senha deve ter no mínimo {PASSWORD_MIN} caracteres"
    if len(password) > 128:
        return "Senha muito longa"
    if not re.search(r"[A-Za-z]", password) or not re.search(r"[0-9]", password):
        return "A senha deve conter letras e números"
    return None


def set_user_session(user, sess) -> None:
    session.clear()
    session.permanent = True
    session["user_id"] = user.id
    session["user_email"] = user.email or ""
    session["access_token"] = sess.access_token
    if sess.refresh_token:
        session["refresh_token"] = sess.refresh_token
    session.modified = True


# ---------------------------------------------------------------------------
# Security headers
# ---------------------------------------------------------------------------
@app.after_request
def set_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    if IS_PROD:
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
    # CSP básica (permite Google Fonts e o próprio host)
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com data:; "
        "img-src 'self' data:; "
        "connect-src 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    )
    return response


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    if not session.get("user_id"):
        return redirect(url_for("login_page"))
    return render_template("index.html", user_email=session.get("user_email", ""))


@app.route("/login")
def login_page():
    if session.get("user_id"):
        return redirect(url_for("index"))
    return render_template("login.html")


@app.route("/register")
def register_page():
    if session.get("user_id"):
        return redirect(url_for("index"))
    return render_template("register.html")


# ---------------------------------------------------------------------------
# Auth API
# ---------------------------------------------------------------------------
@app.route("/api/auth/register", methods=["POST"])
@limiter.limit("5 per minute")
@limiter.limit("20 per hour")
def api_register():
    data = request.get_json(silent=True) or {}
    email = validate_email(data.get("email") or "")
    password = data.get("password") or ""
    name = (data.get("name") or "").strip()[:80]

    if not email:
        return public_error("E-mail inválido")
    pwd_err = validate_password(password)
    if pwd_err:
        return public_error(pwd_err)

    try:
        client = get_anon_client()
        payload: dict = {"email": email, "password": password}
        if name:
            payload["options"] = {"data": {"name": name}}
        res = client.auth.sign_up(payload)

        user = res.user
        if not user:
            return public_error("Não foi possível criar a conta")

        if res.session and res.session.access_token:
            set_user_session(user, res.session)
            return jsonify({
                "ok": True,
                "user": {"id": user.id, "email": user.email},
                "needs_confirmation": False,
            }), 201

        return jsonify({
            "ok": True,
            "needs_confirmation": True,
            "message": (
                "Conta criada. Verifique seu e-mail para confirmar o cadastro "
                "antes de entrar."
            ),
        }), 201

    except AuthApiError as e:
        msg = (e.message or str(e)).lower()
        if "already" in msg or "registered" in msg:
            return public_error("Este e-mail já está cadastrado", 409)
        return public_error("Não foi possível criar a conta", 400)
    except Exception as e:
        if not IS_PROD:
            return public_error(str(e), 400)
        return public_error("Não foi possível criar a conta", 400)


@app.route("/api/auth/login", methods=["POST"])
@limiter.limit("5 per minute")
@limiter.limit("30 per hour")
def api_login():
    data = request.get_json(silent=True) or {}
    email = validate_email(data.get("email") or "")
    password = data.get("password") or ""

    if not email or not password:
        return public_error("E-mail e senha são obrigatórios")

    try:
        client = get_anon_client()
        res = client.auth.sign_in_with_password(
            {"email": email, "password": password}
        )
        user = res.user
        sess = res.session
        if not user or not sess:
            return public_error("E-mail ou senha incorretos", 401)

        set_user_session(user, sess)
        return jsonify({
            "ok": True,
            "user": {"id": user.id, "email": user.email},
        })
    except AuthApiError as e:
        msg = (e.message or str(e)).lower()
        if "email not confirmed" in msg:
            return public_error(
                "Confirme seu e-mail antes de entrar. Verifique sua caixa de entrada.",
                403,
            )
        return public_error("E-mail ou senha incorretos", 401)
    except Exception:
        return public_error("E-mail ou senha incorretos", 401)


@app.route("/api/auth/logout", methods=["POST"])
@login_required
def api_logout():
    try:
        client = get_user_client()
        if client:
            client.auth.sign_out()
    except Exception:
        pass
    session.clear()
    return jsonify({"ok": True})


@app.route("/api/auth/me", methods=["GET"])
@login_required
def api_me():
    return jsonify({
        "id": session["user_id"],
        "email": session.get("user_email"),
    })


# ---------------------------------------------------------------------------
# Workspaces API (RLS via JWT do usuário)
# ---------------------------------------------------------------------------
@app.route("/api/workspaces", methods=["GET"])
@login_required
def list_workspaces():
    client = get_user_client()
    if not client:
        session.clear()
        return jsonify({"error": "Sessão expirada"}), 401
    try:
        res = (
            client.table("workspaces")
            .select("*")
            .order("created_at")
            .execute()
        )
        return jsonify(res.data or [])
    except Exception as e:
        return public_error(str(e) if not IS_PROD else "Erro ao listar workspaces", 500)


@app.route("/api/workspaces", methods=["POST"])
@login_required
@limiter.limit("30 per minute")
def create_workspace():
    client = get_user_client()
    if not client:
        session.clear()
        return jsonify({"error": "Sessão expirada"}), 401

    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return public_error("Nome é obrigatório")
    if len(name) > 60:
        return public_error("Nome muito longo (máx. 60)")

    ws = {
        "id": uid(),
        "user_id": current_user_id(),
        "name": name,
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    try:
        res = client.table("workspaces").insert(ws).execute()
        return jsonify((res.data or [ws])[0]), 201
    except Exception as e:
        return public_error(str(e) if not IS_PROD else "Erro ao criar workspace", 400)


@app.route("/api/workspaces/<ws_id>", methods=["PUT"])
@login_required
def update_workspace(ws_id):
    client = get_user_client()
    if not client:
        session.clear()
        return jsonify({"error": "Sessão expirada"}), 401

    if not re.fullmatch(r"[a-f0-9]{12}", ws_id or ""):
        return public_error("ID inválido", 400)

    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return public_error("Nome é obrigatório")
    if len(name) > 60:
        return public_error("Nome muito longo (máx. 60)")

    try:
        res = (
            client.table("workspaces")
            .update({"name": name, "updated_at": now_iso()})
            .eq("id", ws_id)
            .execute()
        )
        if not res.data:
            return public_error("Workspace não encontrado", 404)
        return jsonify(res.data[0])
    except Exception as e:
        return public_error(str(e) if not IS_PROD else "Erro ao atualizar", 400)


@app.route("/api/workspaces/<ws_id>", methods=["DELETE"])
@login_required
def delete_workspace(ws_id):
    client = get_user_client()
    if not client:
        session.clear()
        return jsonify({"error": "Sessão expirada"}), 401

    if not re.fullmatch(r"[a-f0-9]{12}", ws_id or ""):
        return public_error("ID inválido", 400)

    try:
        # RLS garante que só apaga os próprios; CASCADE no banco remove tasks
        client.table("tasks").delete().eq("workspace_id", ws_id).execute()
        res = client.table("workspaces").delete().eq("id", ws_id).execute()
        if not res.data:
            return public_error("Workspace não encontrado", 404)
        return jsonify({"ok": True})
    except Exception as e:
        return public_error(str(e) if not IS_PROD else "Erro ao excluir", 400)


# ---------------------------------------------------------------------------
# Tasks API
# ---------------------------------------------------------------------------
@app.route("/api/workspaces/<ws_id>/tasks", methods=["GET"])
@login_required
def list_tasks(ws_id):
    client = get_user_client()
    if not client:
        session.clear()
        return jsonify({"error": "Sessão expirada"}), 401

    if not re.fullmatch(r"[a-f0-9]{12}", ws_id or ""):
        return public_error("ID inválido", 400)

    try:
        ws = (
            client.table("workspaces")
            .select("id")
            .eq("id", ws_id)
            .execute()
        )
        if not ws.data:
            return public_error("Workspace não encontrado", 404)

        res = (
            client.table("tasks")
            .select("*")
            .eq("workspace_id", ws_id)
            .order("updated_at", desc=True)
            .execute()
        )
        return jsonify(res.data or [])
    except Exception as e:
        return public_error(str(e) if not IS_PROD else "Erro ao listar tarefas", 500)


@app.route("/api/workspaces/<ws_id>/tasks", methods=["POST"])
@login_required
@limiter.limit("60 per minute")
def create_task(ws_id):
    client = get_user_client()
    if not client:
        session.clear()
        return jsonify({"error": "Sessão expirada"}), 401

    if not re.fullmatch(r"[a-f0-9]{12}", ws_id or ""):
        return public_error("ID inválido", 400)

    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    description = (data.get("description") or "").strip()
    status = data.get("status") or "pendente"

    if not title:
        return public_error("Título é obrigatório")
    if len(title) > 120:
        return public_error("Título muito longo (máx. 120)")
    if status not in STATUSES:
        return public_error("Status inválido")

    try:
        ws = (
            client.table("workspaces")
            .select("id")
            .eq("id", ws_id)
            .execute()
        )
        if not ws.data:
            return public_error("Workspace não encontrado", 404)

        task = {
            "id": uid(),
            "workspace_id": ws_id,
            "user_id": current_user_id(),
            "title": title,
            "description": description[:500],
            "status": status,
            "created_at": now_iso(),
            "updated_at": now_iso(),
        }
        res = client.table("tasks").insert(task).execute()
        return jsonify((res.data or [task])[0]), 201
    except Exception as e:
        return public_error(str(e) if not IS_PROD else "Erro ao criar tarefa", 400)


@app.route("/api/tasks/<task_id>", methods=["PUT"])
@login_required
def update_task(task_id):
    client = get_user_client()
    if not client:
        session.clear()
        return jsonify({"error": "Sessão expirada"}), 401

    if not re.fullmatch(r"[a-f0-9]{12}", task_id or ""):
        return public_error("ID inválido", 400)

    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    description = data.get("description")
    status = data.get("status")

    if not title:
        return public_error("Título é obrigatório")
    if len(title) > 120:
        return public_error("Título muito longo (máx. 120)")
    if status is not None and status not in STATUSES:
        return public_error("Status inválido")

    payload = {
        "title": title,
        "updated_at": now_iso(),
    }
    if description is not None:
        payload["description"] = str(description).strip()[:500]
    if status is not None:
        payload["status"] = status

    try:
        res = (
            client.table("tasks")
            .update(payload)
            .eq("id", task_id)
            .execute()
        )
        if not res.data:
            return public_error("Tarefa não encontrada", 404)
        return jsonify(res.data[0])
    except Exception as e:
        return public_error(str(e) if not IS_PROD else "Erro ao atualizar tarefa", 400)


@app.route("/api/tasks/<task_id>/status", methods=["PATCH"])
@login_required
def update_task_status(task_id):
    client = get_user_client()
    if not client:
        session.clear()
        return jsonify({"error": "Sessão expirada"}), 401

    if not re.fullmatch(r"[a-f0-9]{12}", task_id or ""):
        return public_error("ID inválido", 400)

    data = request.get_json(silent=True) or {}
    status = data.get("status")
    if status not in STATUSES:
        return public_error("Status inválido")

    try:
        res = (
            client.table("tasks")
            .update({"status": status, "updated_at": now_iso()})
            .eq("id", task_id)
            .execute()
        )
        if not res.data:
            return public_error("Tarefa não encontrada", 404)
        return jsonify(res.data[0])
    except Exception as e:
        return public_error(str(e) if not IS_PROD else "Erro ao atualizar status", 400)


@app.route("/api/tasks/<task_id>", methods=["DELETE"])
@login_required
def delete_task(task_id):
    client = get_user_client()
    if not client:
        session.clear()
        return jsonify({"error": "Sessão expirada"}), 401

    if not re.fullmatch(r"[a-f0-9]{12}", task_id or ""):
        return public_error("ID inválido", 400)

    try:
        res = client.table("tasks").delete().eq("id", task_id).execute()
        if not res.data:
            return public_error("Tarefa não encontrada", 404)
        return jsonify({"ok": True})
    except Exception as e:
        return public_error(str(e) if not IS_PROD else "Erro ao excluir tarefa", 400)


# ---------------------------------------------------------------------------
# Health / errors
# ---------------------------------------------------------------------------
@app.route("/health")
@limiter.exempt
def health():
    missing = check_config()
    return jsonify({"ok": len(missing) == 0, "env": FLASK_ENV})


@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify({"error": "Muitas tentativas. Aguarde um momento e tente de novo."}), 429


@app.errorhandler(404)
def not_found(e):
    if request.path.startswith("/api/"):
        return jsonify({"error": "Não encontrado"}), 404
    return redirect(url_for("login_page"))


@app.errorhandler(500)
def internal_error(e):
    return public_error("Erro interno. Tente novamente.", 500)


# ---------------------------------------------------------------------------
# Entry
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    missing = check_config()
    if missing:
        print("AVISO: variáveis faltando:", ", ".join(missing))
        print("Configure o arquivo .env (veja .env.example e SETUP_SUPABASE.md)")

    # Em desenvolvimento use FLASK_ENV=development no .env
    debug = not IS_PROD
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=debug)
