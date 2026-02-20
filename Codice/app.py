from __future__ import annotations

import os
import random
import re
import hashlib
from datetime import timedelta
from typing import Dict, Optional, Tuple, Any

import mysql.connector
from mysql.connector import Error as MySQLError
from dotenv import load_dotenv
from flask import (
    Flask,
    jsonify,
    redirect,
    render_template,
    render_template_string,
    request,
    send_from_directory,
    session,
    url_for,
)
from werkzeug.security import generate_password_hash, check_password_hash

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# =========================
# Config
# =========================
load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

app = Flask(__name__)

# Session
app.secret_key = os.getenv("SECRET_KEY", "CHANGE_ME_PLEASE")
app.permanent_session_lifetime = timedelta(hours=int(os.getenv("ADMIN_SESSION_HOURS", "12")))

DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "chatbot")
DB_PORT = int(os.getenv("DB_PORT", "3306"))

SIM_THRESHOLD = float(os.getenv("SIM_THRESHOLD", "0.25"))

# Admin hard-allowlist (username). Default: admin
ADMIN_USERS = {u.strip() for u in (os.getenv("ADMIN_USERS", "admin") or "admin").split(",") if u.strip()}

STOPWORDS = [
    "a", "ad", "al", "alla", "alle", "allo", "ai", "agli", "anche", "che", "chi", "ci", "con", "come",
    "da", "dal", "dalla", "delle", "del", "di", "e", "ed", "è", "gli", "ha", "hai", "ho", "i", "il", "in",
    "io", "la", "le", "lo", "loro", "ma", "mi", "ne", "nel", "nella", "no", "non", "o", "per", "poi",
    "se", "sei", "si", "su", "tra", "un", "una", "uno", "voi"
]

# Cache schema (per non interrogare information_schema ad ogni request)
_SCHEMA_CACHE: Dict[str, Dict[str, bool]] = {}

# =========================
# Helpers
# =========================
def clean_text(text: str) -> str:
    text = (text or "").lower()
    for ch in [".", ",", "!", "?", ":", ";", "(", ")", "[", "]", "{", "}", "'", '"', "-", "_", "/", "\\"]:
        text = text.replace(ch, " ")
    words = text.split()
    new_words = [w for w in words if w not in STOPWORDS]
    return " ".join(new_words)


def get_connection():
    return mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        port=DB_PORT,
    )


def _has_column(conn, table: str, column: str) -> bool:
    """Check colonna esistente (con cache)."""
    key = f"{DB_NAME}.{table}"
    if key not in _SCHEMA_CACHE:
        _SCHEMA_CACHE[key] = {}
    if column in _SCHEMA_CACHE[key]:
        return _SCHEMA_CACHE[key][column]

    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT COUNT(*)
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s AND COLUMN_NAME=%s
            """,
            (DB_NAME, table, column),
        )
        exists = (cur.fetchone()[0] or 0) > 0
        cur.close()
    except Exception:
        exists = False

    _SCHEMA_CACHE[key][column] = bool(exists)
    return bool(exists)


def admin_required():
    if not session.get("admin_user_id"):
        return redirect(url_for("admin_login"))
    return None


def current_user() -> Optional[Dict[str, Any]]:
    uid = session.get("user_id")
    if not uid:
        return None
    return {"id": int(uid), "username": session.get("username") or ""}


def _is_legacy_sha256_hash(pw: str) -> bool:
    return bool(re.fullmatch(r"[0-9a-fA-F]{64}", pw or ""))


def verify_password(stored_password: str, plain_password: str) -> Tuple[bool, bool]:
    """Return (ok, needs_upgrade). Supports both legacy SHA256 hex and werkzeug hashes."""
    stored_password = stored_password or ""
    plain_password = plain_password or ""

    # Werkzeug hashes
    if stored_password.startswith(("scrypt:", "pbkdf2:", "argon2:")):
        try:
            return (check_password_hash(stored_password, plain_password), False)
        except Exception:
            return (False, False)

    # Legacy SHA256 hex
    if _is_legacy_sha256_hash(stored_password):
        digest = hashlib.sha256(plain_password.encode("utf-8")).hexdigest()
        ok = digest.lower() == stored_password.lower()
        return (ok, ok)  # if ok -> upgrade

    return (False, False)


def maybe_upgrade_password(conn, user_id: int, stored_password: str, plain_password: str) -> None:
    ok, needs_upgrade = verify_password(stored_password, plain_password)
    if not ok or not needs_upgrade:
        return
    try:
        new_hash = generate_password_hash(plain_password)
        cur = conn.cursor()
        cur.execute("UPDATE utenti SET password=%s WHERE id=%s", (new_hash, int(user_id)))
        conn.commit()
        cur.close()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass


def create_conversation(conn, user_id: int, title: str) -> int:
    title = (title or "").strip() or "Nuova chat"
    title = title[:120]
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO conversations (user_id, title, created_at, updated_at) VALUES (%s, %s, NOW(), NOW())",
        (int(user_id), title),
    )
    conn.commit()
    cid = int(cur.lastrowid)
    cur.close()
    return cid


def ensure_conversation_belongs(conn, conversation_id: int, user_id: int) -> bool:
    cur = conn.cursor()
    cur.execute(
        "SELECT id FROM conversations WHERE id=%s AND user_id=%s LIMIT 1",
        (int(conversation_id), int(user_id)),
    )
    row = cur.fetchone()
    cur.close()
    return bool(row)


def touch_conversation(conn, conversation_id: int) -> None:
    try:
        cur = conn.cursor()
        cur.execute("UPDATE conversations SET updated_at=NOW() WHERE id=%s", (int(conversation_id),))
        conn.commit()
        cur.close()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass


def insert_log_message(
    user_msg: str,
    reply: str,
    best_score: float,
    matched_id,
    user_id: Optional[int] = None,
    conversation_id: Optional[int] = None,
):
    """Inserisce un log compatibile con schema vecchio e schema nuovo (con conversation_id)."""
    try:
        conn = get_connection()
        cur = conn.cursor()

        resolved = 1 if matched_id else 0
        faq_id_val = matched_id  # può essere None

        has_conv = _has_column(conn, "logs", "conversation_id")

        if has_conv:
            cur.execute(
                "INSERT INTO logs (user_id, conversation_id, messaggio_utente, risposta_bot, similarity, faq_id, resolved) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (
                    int(user_id) if user_id else None,
                    int(conversation_id) if conversation_id else None,
                    user_msg,
                    reply,
                    round(float(best_score), 6),
                    faq_id_val,
                    resolved,
                ),
            )
        else:
            cur.execute(
                "INSERT INTO logs (user_id, messaggio_utente, risposta_bot, similarity, faq_id, resolved) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (int(user_id) if user_id else None, user_msg, reply, round(float(best_score), 6), faq_id_val, resolved),
            )

        conn.commit()
        cur.close()
        conn.close()
    except Exception:
        try:
            cur.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass


# =========================
# Public routes
# =========================
@app.get("/")
def site_home():
    return send_from_directory(STATIC_DIR, "index.html")


@app.get("/health")
def health():
    return jsonify({"ok": True})


# =========================
# Auth (users)
# =========================
@app.get("/auth/me")
def auth_me():
    return jsonify({"user": current_user()})


@app.post("/auth/register")
def auth_register():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = (data.get("password") or "").strip()
    email = (data.get("email") or "").strip() or None

    if not username or not password:
        return jsonify({"ok": False, "error": "Inserisci username e password."}), 400
    if len(username) < 3:
        return jsonify({"ok": False, "error": "Lo username deve avere almeno 3 caratteri."}), 400
    if len(password) < 8:
        return jsonify({"ok": False, "error": "La password deve avere almeno 8 caratteri."}), 400

    pw_hash = generate_password_hash(password)

    conn = get_connection()
    cur = conn.cursor(dictionary=True)

    cur.execute("SELECT id FROM utenti WHERE nome=%s LIMIT 1", (username,))
    if cur.fetchone():
        cur.close()
        conn.close()
        return jsonify({"ok": False, "error": "Username già in uso."}), 409

    if email:
        cur.execute("SELECT id FROM utenti WHERE email=%s LIMIT 1", (email,))
        if cur.fetchone():
            cur.close()
            conn.close()
            return jsonify({"ok": False, "error": "Email già in uso."}), 409

    cur2 = conn.cursor()
    cur2.execute(
        "INSERT INTO utenti (nome, password, email, data_creazione) VALUES (%s, %s, %s, NOW())",
        (username, pw_hash, email),
    )
    conn.commit()
    user_id = int(cur2.lastrowid)
    cur2.close()
    cur.close()
    conn.close()

    # auto-login
    session.permanent = True
    session["user_id"] = user_id
    session["username"] = username

    return jsonify({"ok": True, "user": {"id": user_id, "username": username}})


@app.post("/auth/login")
def auth_login():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = (data.get("password") or "").strip()

    if not username or not password:
        return jsonify({"ok": False, "error": "Inserisci username e password."}), 400

    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT id, nome, password, email FROM utenti WHERE nome=%s LIMIT 1", (username,))
    row = cur.fetchone()
    cur.close()

    if not row:
        conn.close()
        return jsonify({"ok": False, "error": "Credenziali non valide."}), 401

    ok, _needs = verify_password(row.get("password") or "", password)
    if not ok:
        conn.close()
        return jsonify({"ok": False, "error": "Credenziali non valide."}), 401

    maybe_upgrade_password(conn, int(row["id"]), row.get("password") or "", password)
    conn.close()

    session.permanent = True
    session["user_id"] = int(row["id"])
    session["username"] = row.get("nome") or username

    return jsonify({"ok": True, "user": {"id": int(row["id"]), "username": session["username"]}})


@app.post("/auth/logout")
def auth_logout():
    for k in ["user_id", "username"]:
        session.pop(k, None)
    return jsonify({"ok": True})


# =========================
# Conversations API
# =========================
@app.get("/api/conversations")
def api_conversations():
    user = current_user()
    if not user:
        return jsonify({"ok": False, "error": "Non autenticato"}), 401

    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute(
        "SELECT id, title, created_at, updated_at FROM conversations WHERE user_id=%s ORDER BY updated_at DESC",
        (int(user["id"]),),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()

    return jsonify({"ok": True, "conversations": rows})


@app.post("/api/conversations/new")
def api_conversations_new():
    user = current_user()
    if not user:
        return jsonify({"ok": False, "error": "Non autenticato"}), 401

    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip() or "Nuova chat"

    conn = get_connection()
    cid = create_conversation(conn, int(user["id"]), title)
    conn.close()

    return jsonify({"ok": True, "conversation_id": cid})


@app.post("/api/conversations/select")
def api_conversations_select():
    user = current_user()
    if not user:
        return jsonify({"ok": False, "error": "Non autenticato"}), 401

    data = request.get_json(silent=True) or {}
    conversation_id = data.get("conversation_id")

    if not conversation_id:
        return jsonify({"ok": False, "error": "conversation_id mancante"}), 400

    conn = get_connection()
    ok = ensure_conversation_belongs(conn, int(conversation_id), int(user["id"]))
    conn.close()

    if not ok:
        return jsonify({"ok": False, "error": "Conversazione non trovata"}), 404

    return jsonify({"ok": True, "conversation_id": int(conversation_id)})


@app.get("/api/conversations/<int:conversation_id>/messages")
def api_conversation_messages(conversation_id: int):
    user = current_user()
    if not user:
        return jsonify({"ok": False, "error": "Non autenticato"}), 401

    conn = get_connection()
    ok = ensure_conversation_belongs(conn, int(conversation_id), int(user["id"]))
    if not ok:
        conn.close()
        return jsonify({"ok": False, "error": "Conversazione non trovata"}), 404

    # logs: recupera ultimi messaggi per questa conversazione (se colonna esiste)
    has_conv = _has_column(conn, "logs", "conversation_id")
    cur = conn.cursor(dictionary=True)

    if has_conv:
        cur.execute(
            """
            SELECT id, data_ora, messaggio_utente, risposta_bot, similarity, faq_id, resolved
            FROM logs
            WHERE user_id=%s AND conversation_id=%s
            ORDER BY id ASC
            LIMIT 500
            """,
            (int(user["id"]), int(conversation_id)),
        )
    else:
        # fallback: non possiamo filtrare per conversation_id
        cur.execute(
            """
            SELECT id, data_ora, messaggio_utente, risposta_bot, similarity, faq_id, resolved
            FROM logs
            WHERE user_id=%s
            ORDER BY id DESC
            LIMIT 200
            """,
            (int(user["id"]),),
        )

    rows = cur.fetchall()
    cur.close()
    conn.close()

    return jsonify({"ok": True, "messages": rows})


# =========================
# Static assets
# =========================
@app.get("/static/<path:filename>")
def static_files(filename: str):
    return send_from_directory(STATIC_DIR, filename)


# =========================
# Chat endpoint
# =========================
@app.post("/chat")
def chat():
    data = request.get_json(silent=True) or {}
    user_msg = (data.get("message") or "").strip()
    conversation_id = data.get("conversation_id")

    user = current_user()
    user_id = int(user["id"]) if user else None

    if not user_msg:
        return jsonify({"reply": "Scrivi un messaggio valido.", "faq_matched_id": None, "conversation_id": conversation_id})

    # Se loggato e non c'è conversation_id -> creane una nuova
    if user_id and not conversation_id:
        try:
            conn = get_connection()
            # titolo dalla prima frase
            title = user_msg[:60].strip() or "Nuova chat"
            conversation_id = create_conversation(conn, user_id, title)
            conn.close()
        except Exception:
            conversation_id = None

    # Se conversation_id presente, verifica appartenenza
    if user_id and conversation_id:
        try:
            conn = get_connection()
            ok = ensure_conversation_belongs(conn, int(conversation_id), user_id)
            conn.close()
            if not ok:
                conversation_id = None
        except Exception:
            conversation_id = None

    # Prendo tutte le FAQ
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT id, domanda, risposta1, risposta2, risposta3 FROM faq")
    faqs = cur.fetchall()
    cur.close()
    conn.close()

    if not faqs:
        return jsonify({"reply": "Al momento non ho contenuti disponibili.", "faq_matched_id": None, "conversation_id": conversation_id})

    domande_pulite = [clean_text(row["domanda"]) for row in faqs]
    user_clean = clean_text(user_msg)

    if user_clean == "":
        return jsonify({"reply": "Puoi riformulare con più dettagli?", "faq_matched_id": None, "conversation_id": conversation_id})

    vectorizer = TfidfVectorizer()
    X = vectorizer.fit_transform(domande_pulite + [user_clean])
    sim = cosine_similarity(X[-1], X[:-1])[0]

    best_index = int(sim.argmax())
    best_score = float(sim[best_index])

    matched_id = None
    reply = "Non ho trovato una risposta precisa."

    if best_score >= SIM_THRESHOLD:
        best_row = faqs[best_index]
        risposte = [r for r in (best_row.get("risposta1"), best_row.get("risposta2"), best_row.get("risposta3")) if r]
        reply = random.choice(risposte) if risposte else "Non ho una risposta precisa."
        matched_id = best_row["id"]

    insert_log_message(
        user_msg=user_msg,
        reply=reply,
        best_score=best_score,
        matched_id=matched_id,
        user_id=user_id,
        conversation_id=conversation_id,
    )

    if user_id and conversation_id:
        try:
            conn = get_connection()
            touch_conversation(conn, conversation_id)
            conn.close()
        except Exception:
            pass

    return jsonify(
        {
            "reply": reply,
            "faq_matched_id": matched_id,
            "similarity": round(best_score, 3),
            "conversation_id": conversation_id,
        }
    )


# =========================
# Admin UI (templates)
# =========================
@app.get("/admin/login")
def admin_login():
    if session.get("admin_user_id"):
        return redirect(url_for("admin_dashboard"))
    return render_template("admin_login.html", error=None)


@app.post("/admin/login")
def admin_login_post():
    username = (request.form.get("username") or "").strip()
    password = (request.form.get("password") or "").strip()

    if not username or not password:
        return render_template("admin_login.html", error="Inserisci username e password.")

    # Admin consentiti solo in allowlist (env ADMIN_USERS, default: admin)
    if username not in ADMIN_USERS:
        return render_template("admin_login.html", error="Utente non autorizzato.")

    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT id, nome, password, email FROM utenti WHERE nome=%s LIMIT 1", (username,))
    row = cur.fetchone()
    cur.close()

    if not row:
        conn.close()
        return render_template("admin_login.html", error="Credenziali non valide.")

    ok, _needs = verify_password(row.get("password") or "", password)
    if not ok:
        conn.close()
        return render_template("admin_login.html", error="Credenziali non valide.")

    maybe_upgrade_password(conn, int(row["id"]), row.get("password") or "", password)
    conn.close()

    session.permanent = True
    session["admin_user_id"] = int(row["id"])
    session["admin_username"] = row.get("nome") or username
    session["admin_email"] = row.get("email") or ""
    return redirect(url_for("admin_dashboard"))


@app.get("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("admin_login"))


# -------------------------
# (RESTO ADMIN INVARIATO)
# -------------------------
@app.get("/admin")
def admin_dashboard():
    redir = admin_required()
    if redir:
        return redir

    conn = get_connection()
    cur = conn.cursor(dictionary=True)

    cur.execute("SELECT COUNT(*) AS c FROM faq")
    faq_count = int(cur.fetchone()["c"])

    cur.execute("SELECT COUNT(*) AS c FROM logs")
    log_count = int(cur.fetchone()["c"])

    cur.execute(
        """
        SELECT DATE(data_ora) AS d, COUNT(*) AS c
        FROM logs
        GROUP BY DATE(data_ora)
        ORDER BY d DESC
        LIMIT 14
        """
    )
    daily = cur.fetchall()

    cur.execute(
        """
        SELECT resolved, COUNT(*) AS c
        FROM logs
        GROUP BY resolved
        """
    )
    resolved_rows = cur.fetchall()

    cur.close()
    conn.close()

    resolved_map = {int(r["resolved"]): int(r["c"]) for r in resolved_rows}
    resolved_ok = resolved_map.get(1, 0)
    resolved_no = resolved_map.get(0, 0)

    return render_template(
        "admin_dashboard.html",
        title="Admin - Report",
        faq_count=faq_count,
        log_count=log_count,
        resolved_ok=resolved_ok,
        resolved_no=resolved_no,
        daily=daily,
        admin_username=session.get("admin_username") or "admin",
    )


@app.get("/admin/faqs")
def admin_faqs():
    redir = admin_required()
    if redir:
        return redir

    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT id, categoria, domanda, data_aggiornamento FROM faq ORDER BY id DESC")
    rows = cur.fetchall()
    cur.close()
    conn.close()

    # Troncamento domanda lato server per tabella
    for r in rows:
        d = (r.get("domanda") or "")
        if len(d) > 120:
            r["domanda_short"] = d[:120] + "…"
        else:
            r["domanda_short"] = d

    return render_template(
        "admin_faqs.html",
        title="Admin - FAQ",
        rows=rows,
        admin_username=session.get("admin_username") or "admin",
    )


@app.get("/admin/faqs/new")
def admin_faq_new():
    redir = admin_required()
    if redir:
        return redir
    return render_template(
        "admin_faq_form.html",
        title="Admin - Nuova FAQ",
        heading="Nuova FAQ",
        faq=None,
        error=None,
        form_action=url_for("admin_faq_new_post"),
        admin_username=session.get("admin_username") or "admin",
    )


@app.post("/admin/faqs/new")
def admin_faq_new_post():
    redir = admin_required()
    if redir:
        return redir

    categoria = (request.form.get("categoria") or "generale").strip() or "generale"
    domanda = (request.form.get("domanda") or "").strip()
    risposta1 = (request.form.get("risposta1") or "").strip() or None
    risposta2 = (request.form.get("risposta2") or "").strip() or None
    risposta3 = (request.form.get("risposta3") or "").strip() or None

    if not domanda:
        return render_template(
            "admin_faq_form.html",
            title="Admin - Nuova FAQ",
            heading="Nuova FAQ",
            faq={"categoria": categoria, "domanda": domanda, "risposta1": risposta1 or "", "risposta2": risposta2 or "", "risposta3": risposta3 or ""},
            error="La domanda è obbligatoria.",
            form_action=url_for("admin_faq_new_post"),
            admin_username=session.get("admin_username") or "admin",
        )

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO faq (categoria, domanda, risposta1, risposta2, risposta3) VALUES (%s, %s, %s, %s, %s)",
        (categoria, domanda, risposta1, risposta2, risposta3),
    )
    conn.commit()
    cur.close()
    conn.close()

    return redirect(url_for("admin_faqs"))


@app.get("/admin/faqs/edit/<int:faq_id>")
def admin_faq_edit(faq_id: int):
    redir = admin_required()
    if redir:
        return redir

    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM faq WHERE id=%s LIMIT 1", (faq_id,))
    faq = cur.fetchone()
    cur.close()
    conn.close()

    if not faq:
        return redirect(url_for("admin_faqs"))

    return render_template(
        "admin_faq_form.html",
        title=f"Admin - Modifica FAQ {faq_id}",
        heading=f"Modifica FAQ #{faq_id}",
        faq=faq,
        error=None,
        form_action=url_for("admin_faq_edit_post", faq_id=faq_id),
        admin_username=session.get("admin_username") or "admin",
    )


@app.post("/admin/faqs/edit/<int:faq_id>")
def admin_faq_edit_post(faq_id: int):
    redir = admin_required()
    if redir:
        return redir

    categoria = (request.form.get("categoria") or "generale").strip() or "generale"
    domanda = (request.form.get("domanda") or "").strip()
    risposta1 = (request.form.get("risposta1") or "").strip() or None
    risposta2 = (request.form.get("risposta2") or "").strip() or None
    risposta3 = (request.form.get("risposta3") or "").strip() or None

    if not domanda:
        return render_template(
            "admin_faq_form.html",
            title=f"Admin - Modifica FAQ {faq_id}",
            heading=f"Modifica FAQ #{faq_id}",
            faq={"categoria": categoria, "domanda": domanda, "risposta1": risposta1 or "", "risposta2": risposta2 or "", "risposta3": risposta3 or ""},
            error="La domanda è obbligatoria.",
            form_action=url_for("admin_faq_edit_post", faq_id=faq_id),
            admin_username=session.get("admin_username") or "admin",
        )

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE faq
        SET categoria=%s, domanda=%s, risposta1=%s, risposta2=%s, risposta3=%s
        WHERE id=%s
        """,
        (categoria, domanda, risposta1, risposta2, risposta3, faq_id),
    )
    conn.commit()
    cur.close()
    conn.close()

    return redirect(url_for("admin_faqs"))


@app.post("/admin/faqs/delete/<int:faq_id>")
def admin_faq_delete(faq_id: int):
    redir = admin_required()
    if redir:
        return redir

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM faq WHERE id=%s", (faq_id,))
    conn.commit()
    cur.close()
    conn.close()

    return redirect(url_for("admin_faqs"))


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True, use_reloader=False)