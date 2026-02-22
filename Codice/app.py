from __future__ import annotations

import os
import random
import re
import hashlib
import json
import urllib.request
import urllib.error

from datetime import timedelta, datetime, date
from typing import Optional, Dict, Any, List

import mysql.connector
from dotenv import load_dotenv
from flask import (
    Flask,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# =========================
# Config
# =========================
load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

app = Flask(__name__, static_folder="static", template_folder="templates")

# Session
app.secret_key = os.getenv("SECRET_KEY", "CHANGE_ME_PLEASE")
app.permanent_session_lifetime = timedelta(hours=int(os.getenv("ADMIN_SESSION_HOURS", "12")))

DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "chatbot")
DB_PORT = int(os.getenv("DB_PORT", "3306"))

SIM_THRESHOLD = float(os.getenv("SIM_THRESHOLD", "0.25"))

# Ticket URL (WHMCS)
TICKET_URL = os.getenv(
    "TICKET_URL",
    "https://shop.serverweb.net/submitticket.php?step=2&deptid=2",
)

# Humanize replies via OpenAI (optional)
HUMANIZE_ENABLED = (os.getenv("HUMANIZE_ENABLED", "1").strip() == "1")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.2").strip()
OPENAI_TEMPERATURE = float(os.getenv("OPENAI_TEMPERATURE", "0.3"))
OPENAI_TIMEOUT_SEC = int(os.getenv("OPENAI_TIMEOUT_SEC", "12"))

# Admin hard-allowlist (username). Default: admin
ADMIN_USERS = {u.strip() for u in (os.getenv("ADMIN_USERS", "admin") or "admin").split(",") if u.strip()}


# =========================
# DB helpers
# =========================

def get_connection():
    return mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        port=DB_PORT,
    )


def table_has_column(conn, table: str, column: str) -> bool:
    cur = conn.cursor()
    cur.execute(
        """
        SELECT COUNT(*)
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s AND COLUMN_NAME=%s
        """,
        (DB_NAME, table, column),
    )
    ok = (cur.fetchone() or [0])[0] > 0
    cur.close()
    return bool(ok)


# =========================
# JSON helpers
# =========================

def _dt_to_str(v: Any) -> Any:
    if isinstance(v, datetime):
        # MySQL timestamp/datetime -> "YYYY-MM-DD HH:MM:SS"
        return v.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(v, date):
        return v.strftime("%Y-%m-%d")
    return v


def _normalize_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for r in rows or []:
        rr = {k: _dt_to_str(v) for k, v in (r or {}).items()}
        out.append(rr)
    return out


# =========================
# Text helpers
# =========================

def _extract_output_text_from_openai_response(payload: dict) -> str:
    if isinstance(payload, dict) and isinstance(payload.get("output_text"), str) and payload["output_text"].strip():
        return payload["output_text"].strip()

    out = payload.get("output")
    if not isinstance(out, list):
        return ""
    parts = []
    for item in out:
        if not isinstance(item, dict):
            continue
        content = item.get("content")
        if not isinstance(content, list):
            continue
        for c in content:
            if not isinstance(c, dict):
                continue
            t = c.get("type")
            if t in ("output_text", "text") and isinstance(c.get("text"), str):
                parts.append(c["text"])
    return "\n".join([p for p in parts if p]).strip()


def humanize_answer(user_question: str, skeleton_answer: str) -> str:
    """Riscrive la risposta rendendola più naturale SENZA aggiungere nuove info.
    Se OPENAI_API_KEY non è impostata o HUMANIZE_ENABLED=0 -> ritorna skeleton_answer.
    """
    if not HUMANIZE_ENABLED or not OPENAI_API_KEY:
        return skeleton_answer

    instructions = (
        "Sei Utixo Copilot, assistente tecnico di Utixo. "
        "Il tuo compito è RISCRIVERE una risposta esistente rendendola più umana, chiara e ben formattata.\n\n"
        "REGOLE OBBLIGATORIE:\n"
        "1) NON aggiungere informazioni nuove non presenti nella risposta base.\n"
        "2) NON inventare passaggi, link, prezzi, nomi di prodotti o procedure.\n"
        "3) Mantieni TUTTI i punti importanti della risposta base (lo 'scheletro').\n"
        "4) Se la risposta base è troppo corta o ambigua, NON espandere: al massimo fai una domanda di chiarimento in chiusura.\n"
        "5) Rispondi in italiano.\n"
        "6) Usa paragrafi brevi e, se utile, punti elenco."
    )

    user_input = (
        "DOMANDA UTENTE:\n"
        f"{user_question.strip()}\n\n"
        "RISPOSTA BASE (da mantenere come contenuto, ma riscrivi tono/forma):\n"
        f"{skeleton_answer.strip()}\n\n"
        "Ora riscrivi la risposta rispettando le REGOLE."
    )

    body = {
        "model": OPENAI_MODEL,
        "instructions": instructions,
        "input": user_input,
        "temperature": OPENAI_TEMPERATURE,
    }

    req = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=OPENAI_TIMEOUT_SEC) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            payload = json.loads(raw)
            out_text = _extract_output_text_from_openai_response(payload)
            return out_text if out_text else skeleton_answer
    except Exception:
        return skeleton_answer


def clean_text(text: str) -> str:
    t = (text or "").lower()
    t = re.sub(r"[^\w\s]", " ", t, flags=re.UNICODE)
    t = re.sub(r"\s+", " ", t).strip()
    return t


# =========================
# Auth helpers
# =========================

def current_user() -> Optional[Dict[str, Any]]:
    uid = session.get("user_id")
    uname = session.get("username")
    if uid and uname:
        return {"id": int(uid), "username": uname}
    return None


def set_user_session(user_id: int, username: str):
    session.permanent = True
    session["user_id"] = int(user_id)
    session["username"] = username


def clear_user_session():
    session.pop("user_id", None)
    session.pop("username", None)


# =========================
# Password helpers (upgrade legacy hashes)
# =========================

def is_sha256_hex(s: str) -> bool:
    return bool(re.fullmatch(r"[0-9a-fA-F]{64}", (s or "").strip()))


def sha256_hex(password: str) -> str:
    return hashlib.sha256((password or "").encode("utf-8")).hexdigest()


def check_password_and_upgrade(conn, user_id: int, password_plain: str, stored_hash: str) -> bool:
    """Supporta:
    - legacy: SHA256 hexdigest
    - nuovo: werkzeug (pbkdf2:sha256, scrypt, etc)
    """
    try:
        from werkzeug.security import check_password_hash, generate_password_hash
    except Exception:
        return sha256_hex(password_plain) == (stored_hash or "")

    stored_hash = (stored_hash or "").strip()

    if is_sha256_hex(stored_hash):
        ok = sha256_hex(password_plain) == stored_hash.lower()
        if ok:
            new_hash = generate_password_hash(password_plain)
            cur = conn.cursor()
            cur.execute("UPDATE utenti SET password=%s WHERE id=%s", (new_hash, int(user_id)))
            conn.commit()
            cur.close()
        return ok

    return check_password_hash(stored_hash, password_plain)


def hash_password_new(password_plain: str) -> str:
    try:
        from werkzeug.security import generate_password_hash
        return generate_password_hash(password_plain)
    except Exception:
        return sha256_hex(password_plain)


# =========================
# Static routes
# =========================

@app.get("/")
def home():
    return send_from_directory(STATIC_DIR, "index.html")


@app.get("/static/<path:filename>")
def static_files(filename: str):
    return send_from_directory(STATIC_DIR, filename)


@app.get("/favicon.ico")
def favicon():
    # opzionale: metti un favicon.ico in static/
    try:
        return send_from_directory(STATIC_DIR, "favicon.ico")
    except Exception:
        return ("", 204)


# =========================
# Auth endpoints
# =========================

@app.get("/me")
def me():
    return jsonify({"user": current_user()})


@app.get("/auth/me")
def auth_me_alias():
    # alias richiesto dal frontend
    return me()


@app.post("/auth/register")
def register():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = (data.get("password") or "").strip()
    email = (data.get("email") or "").strip()

    if not username or not password:
        return jsonify({"ok": False, "error": "Username e password obbligatori."}), 400

    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT id FROM utenti WHERE nome=%s LIMIT 1", (username,))
    if cur.fetchone():
        cur.close()
        conn.close()
        return jsonify({"ok": False, "error": "Username già esistente."}), 400

    pw_hash = hash_password_new(password)
    cur2 = conn.cursor()
    cur2.execute(
        "INSERT INTO utenti (nome, password, email) VALUES (%s, %s, %s)",
        (username, pw_hash, email or None),
    )
    conn.commit()
    user_id = int(cur2.lastrowid)
    cur2.close()
    cur.close()
    conn.close()

    set_user_session(user_id, username)
    return jsonify({"ok": True, "user": {"id": user_id, "username": username}})


@app.post("/auth/login")
def login():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = (data.get("password") or "").strip()

    if not username or not password:
        return jsonify({"ok": False, "error": "Username e password obbligatori."}), 400

    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT id, nome, password FROM utenti WHERE nome=%s LIMIT 1", (username,))
    row = cur.fetchone()
    if not row:
        cur.close()
        conn.close()
        return jsonify({"ok": False, "error": "Credenziali non valide."}), 401

    ok = check_password_and_upgrade(conn, int(row["id"]), password, row["password"])
    cur.close()
    conn.close()

    if not ok:
        return jsonify({"ok": False, "error": "Credenziali non valide."}), 401

    set_user_session(int(row["id"]), row["nome"])
    return jsonify({"ok": True, "user": {"id": int(row["id"]), "username": row["nome"]}})


@app.post("/auth/logout")
def logout():
    clear_user_session()
    # se eri anche admin, butta fuori
    session.pop("admin_user_id", None)
    session.pop("admin_username", None)
    return jsonify({"ok": True})


# =========================
# Conversations helpers
# =========================

def create_conversation(conn, user_id: int, title: str) -> int:
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO conversations (user_id, title, created_at, updated_at) VALUES (%s, %s, NOW(), NOW())",
        (int(user_id), title or "Nuova chat"),
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
    ok = cur.fetchone() is not None
    cur.close()
    return bool(ok)


def touch_conversation(conn, conversation_id: int):
    cur = conn.cursor()
    cur.execute("UPDATE conversations SET updated_at=NOW() WHERE id=%s", (int(conversation_id),))
    conn.commit()
    cur.close()


def set_conversation_title(conn, conversation_id: int, user_id: int, title: str) -> bool:
    """Aggiorna il titolo della conversazione se appartiene all'utente."""
    title = (title or "").strip()[:120]
    if not title:
        return False

    if not ensure_conversation_belongs(conn, int(conversation_id), int(user_id)):
        return False

    cur = conn.cursor()
    cur.execute(
        "UPDATE conversations SET title=%s, updated_at=NOW() WHERE id=%s AND user_id=%s",
        (title, int(conversation_id), int(user_id)),
    )
    conn.commit()
    cur.close()
    return True


# =========================
# Conversations API (legacy + new)
# =========================

def _list_conversations_for_user(user_id: int) -> List[Dict[str, Any]]:
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute(
        "SELECT id, title, created_at, updated_at FROM conversations WHERE user_id=%s ORDER BY updated_at DESC",
        (int(user_id),),
    )
    rows = cur.fetchall() or []
    cur.close()
    conn.close()
    return _normalize_rows(rows)


def _get_conversation(user_id: int, conversation_id: int) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute(
        "SELECT id, user_id, title, created_at, updated_at FROM conversations WHERE id=%s AND user_id=%s LIMIT 1",
        (int(conversation_id), int(user_id)),
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    if not row:
        return None
    return {k: _dt_to_str(v) for k, v in row.items()}


def _get_messages(user_id: int, conversation_id: int) -> List[Dict[str, Any]]:
    conn = get_connection()

    if not ensure_conversation_belongs(conn, int(conversation_id), int(user_id)):
        conn.close()
        raise PermissionError("forbidden")

    cur = conn.cursor(dictionary=True)
    # schema reale: logs.messaggio_utente, risposta_bot, data_ora
    cur.execute(
        """
        SELECT messaggio_utente, risposta_bot, data_ora, similarity, faq_id, resolved
        FROM logs
        WHERE conversation_id=%s AND user_id=%s
        ORDER BY id ASC
        """,
        (int(conversation_id), int(user_id)),
    )
    rows = cur.fetchall() or []
    cur.close()
    conn.close()

    # Frontend si aspetta una lista di messaggi con {role, content, created_at}
    messages: List[Dict[str, Any]] = []
    for r in rows:
        r = {k: _dt_to_str(v) for k, v in (r or {}).items()}
        ts = r.get("data_ora")

        user_txt = (r.get("messaggio_utente") or "").strip()
        if user_txt:
            messages.append({"role": "user", "content": user_txt, "created_at": ts})

        bot_txt = (r.get("risposta_bot") or "").strip()
        if bot_txt:
            messages.append({"role": "assistant", "content": bot_txt, "created_at": ts})

    return messages


# --- LEGACY endpoints (vecchio frontend) ---
@app.get("/conversations")
def list_conversations_legacy():
    user = current_user()
    if not user:
        return jsonify({"ok": True, "conversations": []})
    return jsonify({"ok": True, "conversations": _list_conversations_for_user(int(user["id"]))})


@app.get("/conversations/<int:conversation_id>/messages")
def conversation_messages_legacy(conversation_id: int):
    user = current_user()
    if not user:
        return jsonify({"ok": False, "error": "Non autorizzato"}), 401

    try:
        rows = _get_messages(int(user["id"]), int(conversation_id))
    except PermissionError:
        return jsonify({"ok": False, "error": "Non autorizzato"}), 403

    return jsonify({"ok": True, "messages": rows})


# --- NEW endpoints (frontend attuale) ---
@app.get("/api/conversations")
def api_list_conversations():
    user = current_user()
    if not user:
        return jsonify({"ok": True, "conversations": []})
    return jsonify({"ok": True, "conversations": _list_conversations_for_user(int(user["id"]))})


@app.post("/api/conversations")
def api_create_conversation():
    user = current_user()
    if not user:
        return jsonify({"ok": False, "error": "Non autorizzato"}), 401

    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "Nuova chat").strip()[:120]

    conn = get_connection()
    cid = create_conversation(conn, int(user["id"]), title or "Nuova chat")
    conn.close()

    conv = _get_conversation(int(user["id"]), cid)
    return jsonify({"ok": True, "conversation_id": cid, "conversation": conv})


@app.get("/api/conversations/<int:conversation_id>")
def api_get_conversation(conversation_id: int):
    user = current_user()
    if not user:
        return jsonify({"ok": False, "error": "Non autorizzato"}), 401

    conv = _get_conversation(int(user["id"]), int(conversation_id))
    if not conv:
        return jsonify({"ok": False, "error": "Not found"}), 404

    # compatibilità frontend: alcuni client si aspettano anche i messaggi qui
    try:
        rows = _get_messages(int(user["id"]), int(conversation_id))
    except PermissionError:
        return jsonify({"ok": False, "error": "Non autorizzato"}), 403

    return jsonify({"ok": True, "conversation": conv, "messages": rows})
@app.get("/api/conversations/<int:conversation_id>/messages")
def api_get_messages(conversation_id: int):
    user = current_user()
    if not user:
        return jsonify({"ok": False, "error": "Non autorizzato"}), 401

    try:
        rows = _get_messages(int(user["id"]), int(conversation_id))
    except PermissionError:
        return jsonify({"ok": False, "error": "Non autorizzato"}), 403

    return jsonify({"ok": True, "messages": rows})


@app.post("/api/conversations/<int:conversation_id>/messages")
def api_post_message(conversation_id: int):
    """Compatibilità per frontend che manda i messaggi qui invece che su /chat."""
    user = current_user()
    if not user:
        return jsonify({"ok": False, "error": "Non autorizzato"}), 401

    data = request.get_json(silent=True) or {}
    msg = (data.get("message") or "").strip()
    if not msg:
        return jsonify({"ok": False, "error": "Messaggio vuoto"}), 400

    # riusa la stessa logica di /chat
    return _handle_chat(msg, int(user["id"]), int(conversation_id))


# =========================
# Logging
# =========================

def insert_log_message(
    user_msg: str,
    reply: str,
    similarity: float,
    matched_id: Optional[int],
    user_id: Optional[int],
    conversation_id: Optional[int],
):
    try:
        conn = get_connection()
        cur = conn.cursor()
        resolved = 1 if (matched_id is not None and float(similarity) >= SIM_THRESHOLD) else 0
        cur.execute(
            """
            INSERT INTO logs (user_id, conversation_id, messaggio_utente, risposta_bot, similarity, faq_id, resolved)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                int(user_id) if user_id is not None else None,
                int(conversation_id) if conversation_id is not None else None,
                user_msg,
                reply,
                float(similarity),
                int(matched_id) if matched_id is not None else None,
                int(resolved),
            ),
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception:
        pass


# =========================
# Chat core
# =========================

def _handle_chat(user_msg: str, user_id: Optional[int], conversation_id: Optional[int]):
    user_msg = (user_msg or "").strip()

    if not user_msg:
        return jsonify({"ok": True, "reply": "Scrivi un messaggio valido.", "faq_matched_id": None, "conversation_id": conversation_id})

    # Se loggato e non c'è conversation_id -> creane una nuova
    if user_id and not conversation_id:
        try:
            conn = get_connection()
            title = user_msg[:60].strip() or "Nuova chat"
            conversation_id = create_conversation(conn, int(user_id), title)
            conn.close()
        except Exception:
            conversation_id = None

    # Se conversation_id presente, verifica appartenenza
    if user_id and conversation_id:
        try:
            conn = get_connection()
            ok = ensure_conversation_belongs(conn, int(conversation_id), int(user_id))
            conn.close()
            if not ok:
                conversation_id = None
        except Exception:
            conversation_id = None

    # Prendo tutte le FAQ
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT id, domanda, risposta1, risposta2, risposta3 FROM faq")
    faqs = cur.fetchall() or []
    cur.close()
    conn.close()

    if not faqs:
        return jsonify({"ok": True, "reply": "Al momento non ho contenuti disponibili.", "faq_matched_id": None, "conversation_id": conversation_id})

    domande_pulite = [clean_text(row.get("domanda") or "") for row in faqs]
    user_clean = clean_text(user_msg)

    if user_clean == "":
        return jsonify({"ok": True, "reply": "Puoi riformulare con più dettagli?", "faq_matched_id": None, "conversation_id": conversation_id})

    vectorizer = TfidfVectorizer()
    X = vectorizer.fit_transform(domande_pulite + [user_clean])
    sim = cosine_similarity(X[-1], X[:-1])[0]

    best_index = int(sim.argmax())
    best_score = float(sim[best_index])

    matched_id: Optional[int] = None
    reply = "Non ho trovato una risposta precisa."

    if best_score >= SIM_THRESHOLD:
        best_row = faqs[best_index]
        risposte = [r for r in (best_row.get("risposta1"), best_row.get("risposta2"), best_row.get("risposta3")) if r]
        reply = random.choice(risposte) if risposte else "Non ho una risposta precisa."
        matched_id = int(best_row["id"])
        reply = humanize_answer(user_msg, reply)

    insert_log_message(
        user_msg=user_msg,
        reply=reply,
        similarity=best_score,
        matched_id=matched_id,
        user_id=user_id,
        conversation_id=conversation_id,
    )

    if user_id and conversation_id:
        try:
            conn = get_connection()

            # Se la conversazione è stata creata dal frontend con titolo "Nuova chat",
            # al primo messaggio la rinominiamo con l'incipit della chat.
            try:
                cur = conn.cursor(dictionary=True)
                cur.execute(
                    "SELECT title FROM conversations WHERE id=%s AND user_id=%s LIMIT 1",
                    (int(conversation_id), int(user_id)),
                )
                row = cur.fetchone() or {}
                cur.close()
                current_title = (row.get("title") or "").strip().lower()
                if current_title in ("", "nuova chat", "new chat"):
                    new_title = user_msg[:60].strip() or "Nuova chat"
                    set_conversation_title(conn, int(conversation_id), int(user_id), new_title)
            except Exception:
                pass

            touch_conversation(conn, int(conversation_id))
            conn.close()
        except Exception:
            pass

    return jsonify(
        {
            "ok": True,
            "reply": reply,
            "faq_matched_id": matched_id,
            "similarity": round(best_score, 3),
            "conversation_id": conversation_id,
            "ticket_url": TICKET_URL,
        }
    )


# =========================
# Chat endpoints
# =========================

@app.post("/chat")
def chat():
    data = request.get_json(silent=True) or {}
    # compatibilità: alcuni frontend inviano 'question' invece di 'message'
    user_msg = (data.get("message") or data.get("question") or "").strip()
    conversation_id = data.get("conversation_id")

    user = current_user()
    user_id = int(user["id"]) if user else None

    # conversation_id può arrivare come stringa
    try:
        conversation_id = int(conversation_id) if conversation_id not in (None, "", 0, "0") else None
    except Exception:
        conversation_id = None

    return _handle_chat(user_msg, user_id, conversation_id)

@app.post("/ask")
def ask_alias():
    # alias per vecchi frontend
    return chat()


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

    # Admin consentiti solo in allowlist
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

    ok = check_password_and_upgrade(conn, int(row["id"]), password, row["password"])
    conn.close()
    if not ok:
        return render_template("admin_login.html", error="Credenziali non valide.")

    session.permanent = True
    session["admin_user_id"] = int(row["id"])
    session["admin_username"] = row["nome"]
    return redirect(url_for("admin_dashboard"))


@app.get("/admin/logout")
def admin_logout():
    session.pop("admin_user_id", None)
    session.pop("admin_username", None)
    return redirect(url_for("admin_login"))


def admin_required():
    if not session.get("admin_user_id"):
        return redirect(url_for("admin_login"))
    return None


@app.get("/admin")
def admin_dashboard():
    red = admin_required()
    if red:
        return red

    conn = get_connection()
    cur = conn.cursor(dictionary=True)

    cur.execute("SELECT COUNT(*) AS n FROM faq")
    faq_count = int((cur.fetchone() or {}).get("n", 0))

    cur.execute("SELECT COUNT(*) AS n FROM logs")
    log_count = int((cur.fetchone() or {}).get("n", 0))

    # schema: resolved tinyint(1)
    cur.execute("SELECT COUNT(*) AS n FROM logs WHERE resolved=1")
    resolved_ok = int((cur.fetchone() or {}).get("n", 0))

    cur.execute("SELECT COUNT(*) AS n FROM logs WHERE resolved=0")
    resolved_no = int((cur.fetchone() or {}).get("n", 0))

    # ultimi 14 giorni: group by data_ora
    cur.execute(
        """
        SELECT DATE(data_ora) AS d, COUNT(*) AS c
        FROM logs
        WHERE data_ora >= DATE_SUB(CURDATE(), INTERVAL 14 DAY)
        GROUP BY DATE(data_ora)
        ORDER BY d ASC
        """
    )
    daily = _normalize_rows(cur.fetchall() or [])

    cur.close()
    conn.close()

    return render_template(
        "admin_dashboard.html",
        admin_username=session.get("admin_username") or "admin",
        faq_count=faq_count,
        log_count=log_count,
        resolved_ok=resolved_ok,
        resolved_no=resolved_no,
        daily=daily,
    )


@app.get("/admin/faqs")
def admin_faqs():
    red = admin_required()
    if red:
        return red

    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute(
        "SELECT id, categoria, domanda, data_aggiornamento FROM faq ORDER BY id DESC"
    )
    rows = cur.fetchall() or []
    cur.close()
    conn.close()

    # aggiungi domanda_short per template
    for r in rows:
        d = (r.get("domanda") or "").strip()
        r["domanda_short"] = (d[:90] + "…") if len(d) > 90 else d
        r["data_aggiornamento"] = _dt_to_str(r.get("data_aggiornamento"))

    return render_template("admin_faqs.html", rows=rows)


@app.get("/admin/faqs/new")
def admin_faq_new():
    red = admin_required()
    if red:
        return red

    return render_template(
        "admin_faq_form.html",
        heading="Nuova FAQ",
        form_action="/admin/faqs/new",
        faq=None,
        error=None,
    )


@app.post("/admin/faqs/new")
def admin_faq_new_post():
    red = admin_required()
    if red:
        return red

    categoria = (request.form.get("categoria") or "generale").strip()[:100] or "generale"
    domanda = (request.form.get("domanda") or "").strip()
    r1 = (request.form.get("risposta1") or "").strip()
    r2 = (request.form.get("risposta2") or "").strip()
    r3 = (request.form.get("risposta3") or "").strip()

    if not domanda or not r1:
        return render_template(
            "admin_faq_form.html",
            heading="Nuova FAQ",
            form_action="/admin/faqs/new",
            faq={"categoria": categoria, "domanda": domanda, "risposta1": r1, "risposta2": r2, "risposta3": r3},
            error="Domanda e Risposta 1 sono obbligatorie.",
        )

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO faq (categoria, domanda, risposta1, risposta2, risposta3) VALUES (%s, %s, %s, %s, %s)",
        (categoria, domanda, r1, r2 or None, r3 or None),
    )
    conn.commit()
    cur.close()
    conn.close()

    return redirect("/admin/faqs")


@app.get("/admin/faqs/edit/<int:faq_id>")
def admin_faq_edit(faq_id: int):
    red = admin_required()
    if red:
        return red

    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute(
        "SELECT id, categoria, domanda, risposta1, risposta2, risposta3 FROM faq WHERE id=%s",
        (int(faq_id),),
    )
    faq = cur.fetchone()
    cur.close()
    conn.close()

    if not faq:
        return redirect("/admin/faqs")

    return render_template(
        "admin_faq_form.html",
        heading=f"Modifica FAQ #{faq_id}",
        form_action=f"/admin/faqs/edit/{faq_id}",
        faq=faq,
        error=None,
    )


@app.post("/admin/faqs/edit/<int:faq_id>")
def admin_faq_edit_post(faq_id: int):
    red = admin_required()
    if red:
        return red

    categoria = (request.form.get("categoria") or "generale").strip()[:100] or "generale"
    domanda = (request.form.get("domanda") or "").strip()
    r1 = (request.form.get("risposta1") or "").strip()
    r2 = (request.form.get("risposta2") or "").strip()
    r3 = (request.form.get("risposta3") or "").strip()

    if not domanda or not r1:
        return render_template(
            "admin_faq_form.html",
            heading=f"Modifica FAQ #{faq_id}",
            form_action=f"/admin/faqs/edit/{faq_id}",
            faq={"id": faq_id, "categoria": categoria, "domanda": domanda, "risposta1": r1, "risposta2": r2, "risposta3": r3},
            error="Domanda e Risposta 1 sono obbligatorie.",
        )

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE faq
        SET categoria=%s, domanda=%s, risposta1=%s, risposta2=%s, risposta3=%s
        WHERE id=%s
        """,
        (categoria, domanda, r1, r2 or None, r3 or None, int(faq_id)),
    )
    conn.commit()
    cur.close()
    conn.close()

    return redirect("/admin/faqs")


@app.post("/admin/faqs/delete/<int:faq_id>")
def admin_faq_delete(faq_id: int):
    red = admin_required()
    if red:
        return red

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM faq WHERE id=%s", (int(faq_id),))
    conn.commit()
    cur.close()
    conn.close()

    return redirect("/admin/faqs")


# =========================
# Run
# =========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=True)