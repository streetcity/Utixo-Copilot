from __future__ import annotations

import hashlib
import os
import re
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import mysql.connector
import numpy as np
from dotenv import load_dotenv
from flask import Flask, current_app, jsonify, redirect, render_template, request, send_from_directory, session, url_for
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

load_dotenv(BASE_DIR / ".env")

FAQ_SYNONYMS = {
    "m365": "microsoft 365",
    "office365": "microsoft 365",
    "o365": "microsoft 365",
    "exo": "exchange online",
    "exchangeonline": "exchange online",
    "onedrive": "one drive",
    "sharepointonline": "sharepoint online",
    "teams": "microsoft teams",
    "pwd": "password",
    "pass": "password",
    "2fa": "autenticazione a due fattori",
    "mfa": "autenticazione a due fattori",
}

FAQ_CACHE: Dict[str, Any] = {"fingerprint": None}


def parse_admin_users(raw: Optional[str]) -> set[str]:
    value = raw or "admin"
    return {item.strip() for item in value.split(",") if item.strip()}


def create_app() -> Flask:
    app = Flask(__name__, static_folder=str(STATIC_DIR), template_folder=str(TEMPLATES_DIR))
    app.config.from_mapping(
        {
            "BASE_DIR": str(BASE_DIR),
            "STATIC_DIR": str(STATIC_DIR),
            "TEMPLATES_DIR": str(TEMPLATES_DIR),
            "SECRET_KEY": os.getenv("SECRET_KEY", "CHANGE_ME_PLEASE"),
            "PERMANENT_SESSION_LIFETIME": timedelta(hours=int(os.getenv("ADMIN_SESSION_HOURS", "12"))),
            "DB_HOST": os.getenv("DB_HOST", "127.0.0.1"),
            "DB_USER": os.getenv("DB_USER", "root"),
            "DB_PASSWORD": os.getenv("DB_PASSWORD", ""),
            "DB_NAME": os.getenv("DB_NAME", "chatbot"),
            "DB_PORT": int(os.getenv("DB_PORT", "3306")),
            "SIM_THRESHOLD": float(os.getenv("SIM_THRESHOLD", "0.25")),
            "SIM_ALPHA_WORD": float(os.getenv("SIM_ALPHA_WORD", "0.65")),
            "SIM_LOW_HINT": float(os.getenv("SIM_LOW_HINT", "0.12")),
            "SUGGEST_TOPK": int(os.getenv("SUGGEST_TOPK", "3")),
            "TICKET_URL": os.getenv(
                "TICKET_URL",
                "https://shop.serverweb.net/submitticket.php?step=2&deptid=2",
            ),
            "ADMIN_USERS": parse_admin_users(os.getenv("ADMIN_USERS", "admin")),
            "PORT": int(os.getenv("PORT", "5000")),
            "DEBUG": os.getenv("FLASK_DEBUG", "1").strip() == "1",
        }
    )
    app.secret_key = app.config["SECRET_KEY"]
    app.permanent_session_lifetime = app.config["PERMANENT_SESSION_LIFETIME"]
    register_routes(app)
    return app


# =========================
# Database helpers
# =========================
def get_connection():
    return mysql.connector.connect(
        host=current_app.config["DB_HOST"],
        user=current_app.config["DB_USER"],
        password=current_app.config["DB_PASSWORD"],
        database=current_app.config["DB_NAME"],
        port=current_app.config["DB_PORT"],
    )


# =========================
# Auth helpers
# =========================
def current_user() -> Optional[Dict[str, Any]]:
    uid = session.get("user_id")
    username = session.get("username")
    if uid and username:
        return {"id": int(uid), "username": username}
    return None



def set_user_session(user_id: int, username: str):
    session.permanent = True
    session["user_id"] = int(user_id)
    session["username"] = username



def clear_user_session():
    session.pop("user_id", None)
    session.pop("username", None)



def is_sha256_hex(value: str) -> bool:
    return bool(re.fullmatch(r"[0-9a-fA-F]{64}", (value or "").strip()))



def sha256_hex(password: str) -> str:
    return hashlib.sha256((password or "").encode("utf-8")).hexdigest()



def check_password_and_upgrade(conn, user_id: int, password_plain: str, stored_hash: str) -> bool:
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
    return generate_password_hash(password_plain)


# =========================
# Text / FAQ helpers
# =========================
def apply_synonyms(text: str) -> str:
    value = text
    for key, replacement in FAQ_SYNONYMS.items():
        value = re.sub(rf"\b{re.escape(key)}\b", replacement, value)
    return value



def clean_text(text: str) -> str:
    value = (text or "").lower()
    value = apply_synonyms(value)
    value = re.sub(r"[^\w\s]", " ", value, flags=re.UNICODE)
    value = re.sub(r"\s+", " ", value).strip()
    return value



def humanize_answer(answer: str) -> str:
    value = (answer or "").strip()
    if not value:
        return value

    parts = [p.strip() for p in re.split(r"\n+|\.\s+", value) if p.strip()]
    if len(value) >= 160 and len(parts) >= 4 and not value.lstrip().startswith(("- ", "• ", "1) ", "1. ", "* ")):
        return "\n".join(f"- {p}" for p in parts)

    return value



def get_all_faqs() -> List[Dict[str, Any]]:
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT id, domanda, risposta1, risposta2, risposta3 FROM faq")
    rows = cur.fetchall() or []
    cur.close()
    conn.close()
    return rows



def fingerprint_faqs(faqs: List[Dict[str, Any]]) -> str:
    digest = hashlib.sha256()
    for row in faqs:
        digest.update(str(row.get("id")).encode())
        digest.update((row.get("domanda") or "").encode("utf-8", errors="ignore"))
        digest.update((row.get("risposta1") or "").encode("utf-8", errors="ignore"))
        digest.update((row.get("risposta2") or "").encode("utf-8", errors="ignore"))
        digest.update((row.get("risposta3") or "").encode("utf-8", errors="ignore"))
    return digest.hexdigest()



def build_faq_index(faqs: List[Dict[str, Any]]):
    questions_clean = [clean_text(row.get("domanda") or "") for row in faqs]
    vec_word = TfidfVectorizer(ngram_range=(1, 2), min_df=1)
    x_word = vec_word.fit_transform(questions_clean)
    vec_char = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=1)
    x_char = vec_char.fit_transform(questions_clean)
    return questions_clean, vec_word, x_word, vec_char, x_char



def get_faq_index(faqs: List[Dict[str, Any]]):
    fingerprint = fingerprint_faqs(faqs)
    if FAQ_CACHE.get("fingerprint") != fingerprint:
        questions_clean, vec_word, x_word, vec_char, x_char = build_faq_index(faqs)
        FAQ_CACHE.update(
            {
                "fingerprint": fingerprint,
                "faqs": faqs,
                "questions_clean": questions_clean,
                "vec_word": vec_word,
                "x_word": x_word,
                "vec_char": vec_char,
                "x_char": x_char,
            }
        )
    return FAQ_CACHE



def score_faqs(user_clean: str, cache: Dict[str, Any]):
    q_word = cache["vec_word"].transform([user_clean])
    q_char = cache["vec_char"].transform([user_clean])
    sim_word = cosine_similarity(q_word, cache["x_word"])[0]
    sim_char = cosine_similarity(q_char, cache["x_char"])[0]
    alpha = current_app.config["SIM_ALPHA_WORD"]
    sim = alpha * sim_word + (1.0 - alpha) * sim_char
    return sim, sim_word, sim_char



def match_faq(user_message: str) -> Dict[str, Any]:
    faqs = get_all_faqs()
    if not faqs:
        return {
            "reply": "Al momento non ho contenuti disponibili.",
            "matched_id": None,
            "similarity": 0.0,
            "suggestions": [],
            "need_clarification": False,
        }

    user_clean = clean_text(user_message)
    if not user_clean:
        return {
            "reply": "Puoi riformulare con più dettagli?",
            "matched_id": None,
            "similarity": 0.0,
            "suggestions": [],
            "need_clarification": True,
        }

    cache = get_faq_index(faqs)
    sim, _, _ = score_faqs(user_clean, cache)
    best_index = int(np.argmax(sim))
    best_score = float(sim[best_index])

    top_idx = sim.argsort()[::-1][: max(1, current_app.config["SUGGEST_TOPK"])]
    suggestions = []
    for idx in top_idx:
        row = faqs[int(idx)]
        suggestions.append(
            {
                "id": int(row["id"]),
                "domanda": (row.get("domanda") or "").strip(),
                "score": float(sim[int(idx)]),
            }
        )

    if best_score >= current_app.config["SIM_THRESHOLD"]:
        best_row = faqs[best_index]
        answers = [
            reply
            for reply in (
                best_row.get("risposta1"),
                best_row.get("risposta2"),
                best_row.get("risposta3"),
            )
            if reply
        ]
        return {
            "reply": answers[0] if answers else "Non ho una risposta precisa.",
            "matched_id": int(best_row["id"]),
            "similarity": best_score,
            "suggestions": suggestions,
            "need_clarification": False,
        }

    if suggestions and float(suggestions[0]["score"]) >= current_app.config["SIM_LOW_HINT"]:
        reply = (
            "Non sono sicuro al 100% di cosa intendi. "
            "Puoi dirmi quale di questi casi è più vicino?\n\n"
            + "\n".join([f"{idx + 1}) {item['domanda']}" for idx, item in enumerate(suggestions)])
            + "\n\nRispondi con il numero (1/2/3) oppure aggiungi un dettaglio in più."
        )
    else:
        reply = (
            "Non ho trovato una risposta precisa. "
            "Puoi aggiungere un dettaglio in più, ad esempio prodotto, errore o schermata?"
        )

    return {
        "reply": reply,
        "matched_id": None,
        "similarity": best_score,
        "suggestions": suggestions,
        "need_clarification": True,
    }


# =========================
# Conversation helpers
# =========================
def dt_to_str(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, date):
        return value.strftime("%Y-%m-%d")
    return value



def normalize_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [{k: dt_to_str(v) for k, v in (row or {}).items()} for row in (rows or [])]



def create_conversation(conn, user_id: int, title: str) -> int:
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO conversations (user_id, title, created_at, updated_at) VALUES (%s, %s, NOW(), NOW())",
        (int(user_id), title or "Nuova chat"),
    )
    conn.commit()
    conversation_id = int(cur.lastrowid)
    cur.close()
    return conversation_id



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



def list_conversations_for_user(user_id: int) -> List[Dict[str, Any]]:
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute(
        "SELECT id, title, created_at, updated_at FROM conversations WHERE user_id=%s ORDER BY updated_at DESC",
        (int(user_id),),
    )
    rows = cur.fetchall() or []
    cur.close()
    conn.close()
    return normalize_rows(rows)



def get_conversation(user_id: int, conversation_id: int) -> Optional[Dict[str, Any]]:
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
    return {k: dt_to_str(v) for k, v in row.items()}



def get_messages(user_id: int, conversation_id: int) -> List[Dict[str, Any]]:
    conn = get_connection()
    if not ensure_conversation_belongs(conn, int(conversation_id), int(user_id)):
        conn.close()
        raise PermissionError("forbidden")

    cur = conn.cursor(dictionary=True)
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

    messages: List[Dict[str, Any]] = []
    for row in rows:
        row = {k: dt_to_str(v) for k, v in (row or {}).items()}
        ts = row.get("data_ora")
        user_text = (row.get("messaggio_utente") or "").strip()
        if user_text:
            messages.append({"role": "user", "content": user_text, "created_at": ts})
        bot_text = (row.get("risposta_bot") or "").strip()
        if bot_text:
            messages.append({"role": "assistant", "content": bot_text, "created_at": ts})
    return messages


# =========================
# Chat helpers
# =========================
def insert_log_message(
    user_msg: str,
    reply: str,
    similarity: float,
    matched_id: Optional[int],
    user_id: Optional[int],
    conversation_id: Optional[int],
) -> Optional[int]:
    try:
        conn = get_connection()
        cur = conn.cursor()
        resolved = 1 if (matched_id is not None and float(similarity) >= current_app.config["SIM_THRESHOLD"]) else 0
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
        log_id = int(cur.lastrowid)
        conn.commit()
        cur.close()
        conn.close()
        return log_id
    except Exception:
        return None



def handle_chat(user_msg: str, user_id: Optional[int], conversation_id: Optional[int]):
    user_msg = (user_msg or "").strip()
    if not user_msg:
        return jsonify(
            {
                "ok": True,
                "reply": "Scrivi un messaggio valido.",
                "faq_matched_id": None,
                "conversation_id": conversation_id,
            }
        )

    if user_id and not conversation_id:
        try:
            conn = get_connection()
            title = user_msg[:60].strip() or "Nuova chat"
            conversation_id = create_conversation(conn, int(user_id), title)
            conn.close()
        except Exception:
            conversation_id = None

    if user_id and conversation_id:
        try:
            conn = get_connection()
            ok = ensure_conversation_belongs(conn, int(conversation_id), int(user_id))
            conn.close()
            if not ok:
                conversation_id = None
        except Exception:
            conversation_id = None

    result = match_faq(user_msg)
    matched_id = result["matched_id"]
    similarity = float(result["similarity"])
    reply = result["reply"]

    if matched_id is not None:
        reply = humanize_answer(reply)

    log_id = insert_log_message(
        user_msg=user_msg,
        reply=reply,
        similarity=similarity,
        matched_id=matched_id,
        user_id=user_id,
        conversation_id=conversation_id,
    )

    if user_id and conversation_id:
        try:
            conn = get_connection()
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
            "similarity": round(similarity, 3),
            "conversation_id": conversation_id,
            "ticket_url": current_app.config["TICKET_URL"],
            "log_id": log_id,
            "need_clarification": result["need_clarification"],
            "suggestions": result["suggestions"],
        }
    )


# =========================
# Admin helpers
# =========================
def admin_required():
    if not session.get("admin_user_id"):
        return redirect(url_for("admin_login"))
    return None


# =========================
# Routes
# =========================
def register_routes(app: Flask):
    @app.get("/")
    def home():
        return send_from_directory(current_app.config["STATIC_DIR"], "index.html")

    @app.get("/static/<path:filename>")
    def static_files(filename: str):
        return send_from_directory(current_app.config["STATIC_DIR"], filename)

    @app.get("/favicon.ico")
    def favicon():
        try:
            return send_from_directory(current_app.config["STATIC_DIR"], "favicon.ico")
        except Exception:
            return ("", 204)

    @app.get("/me")
    @app.get("/auth/me")
    def me():
        return jsonify({"user": current_user()})

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
        session.pop("admin_user_id", None)
        session.pop("admin_username", None)
        return jsonify({"ok": True})

    @app.get("/api/conversations")
    def api_list_conversations():
        user = current_user()
        if not user:
            return jsonify({"ok": True, "conversations": []})
        return jsonify({"ok": True, "conversations": list_conversations_for_user(int(user["id"]))})

    @app.post("/api/conversations")
    def api_create_conversation():
        user = current_user()
        if not user:
            return jsonify({"ok": False, "error": "Non autorizzato"}), 401

        data = request.get_json(silent=True) or {}
        title = (data.get("title") or "Nuova chat").strip()[:120]

        conn = get_connection()
        conversation_id = create_conversation(conn, int(user["id"]), title or "Nuova chat")
        conn.close()

        conversation = get_conversation(int(user["id"]), conversation_id)
        return jsonify({"ok": True, "conversation_id": conversation_id, "conversation": conversation})

    @app.get("/api/conversations/<int:conversation_id>")
    def api_get_conversation(conversation_id: int):
        user = current_user()
        if not user:
            return jsonify({"ok": False, "error": "Non autorizzato"}), 401

        conversation = get_conversation(int(user["id"]), int(conversation_id))
        if not conversation:
            return jsonify({"ok": False, "error": "Not found"}), 404

        try:
            rows = get_messages(int(user["id"]), int(conversation_id))
        except PermissionError:
            return jsonify({"ok": False, "error": "Non autorizzato"}), 403

        return jsonify({"ok": True, "conversation": conversation, "messages": rows})

    @app.get("/api/conversations/<int:conversation_id>/messages")
    def api_get_messages(conversation_id: int):
        user = current_user()
        if not user:
            return jsonify({"ok": False, "error": "Non autorizzato"}), 401

        try:
            rows = get_messages(int(user["id"]), int(conversation_id))
        except PermissionError:
            return jsonify({"ok": False, "error": "Non autorizzato"}), 403

        return jsonify({"ok": True, "messages": rows})

    @app.post("/api/conversations/<int:conversation_id>/messages")
    def api_post_message(conversation_id: int):
        user = current_user()
        if not user:
            return jsonify({"ok": False, "error": "Non autorizzato"}), 401

        data = request.get_json(silent=True) or {}
        message = (data.get("message") or "").strip()
        if not message:
            return jsonify({"ok": False, "error": "Messaggio vuoto"}), 400

        return handle_chat(message, int(user["id"]), int(conversation_id))

    @app.post("/chat")
    @app.post("/ask")
    def chat():
        data = request.get_json(silent=True) or {}
        user_msg = (data.get("message") or data.get("question") or "").strip()
        conversation_id = data.get("conversation_id")
        user = current_user()
        user_id = int(user["id"]) if user else None

        try:
            conversation_id = int(conversation_id) if conversation_id not in (None, "", 0, "0") else None
        except Exception:
            conversation_id = None

        return handle_chat(user_msg, user_id, conversation_id)

    @app.post("/feedback")
    def feedback():
        data = request.get_json(silent=True) or {}
        try:
            log_id = int(data.get("log_id"))
        except Exception:
            return jsonify({"ok": False, "error": "log_id non valido"}), 400

        try:
            value = int(data.get("value"))
        except Exception:
            value = 0

        if value not in (1, -1):
            return jsonify({"ok": False, "error": "value deve essere 1 o -1"}), 400

        comment = (data.get("comment") or "").strip()
        if comment:
            comment = comment[:500]

        user = current_user()
        user_id = int(user["id"]) if user else None
        faq_id = None

        conn = None
        try:
            conn = get_connection()
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT faq_id FROM logs WHERE id=%s LIMIT 1", (int(log_id),))
            row = cur.fetchone() or {}
            cur.close()
            faq_id = int(row["faq_id"]) if row.get("faq_id") else None

            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO feedback (log_id, user_id, faq_id, value, comment)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (int(log_id), user_id, faq_id, int(value), comment or None),
            )
            conn.commit()
            cur.close()
        except Exception:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass
            return jsonify({"ok": False, "error": "impossibile salvare feedback"}), 500

        if conn:
            conn.close()
        return jsonify({"ok": True})

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

        if username not in current_app.config["ADMIN_USERS"]:
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

    @app.get("/admin")
    def admin_dashboard():
        redirect_response = admin_required()
        if redirect_response:
            return redirect_response

        conn = get_connection()
        cur = conn.cursor(dictionary=True)

        cur.execute("SELECT COUNT(*) AS n FROM faq")
        faq_count = int((cur.fetchone() or {}).get("n", 0))

        cur.execute("SELECT COUNT(*) AS n FROM logs")
        log_count = int((cur.fetchone() or {}).get("n", 0))

        cur.execute("SELECT COUNT(*) AS n FROM logs WHERE resolved=1")
        resolved_ok = int((cur.fetchone() or {}).get("n", 0))

        cur.execute("SELECT COUNT(*) AS n FROM logs WHERE resolved=0")
        resolved_no = int((cur.fetchone() or {}).get("n", 0))

        cur.execute("SELECT COUNT(*) AS n FROM feedback")
        fb_total = int((cur.fetchone() or {}).get("n", 0))

        cur.execute("SELECT COUNT(*) AS n FROM feedback WHERE value=1")
        fb_up = int((cur.fetchone() or {}).get("n", 0))

        cur.execute("SELECT COUNT(*) AS n FROM feedback WHERE value=-1")
        fb_down = int((cur.fetchone() or {}).get("n", 0))

        fb_rate = round((fb_up / fb_total) * 100, 1) if fb_total > 0 else 0.0

        cur.execute(
            """
            SELECT DATE(data_ora) AS d, COUNT(*) AS c
            FROM logs
            WHERE data_ora >= DATE_SUB(CURDATE(), INTERVAL 14 DAY)
            GROUP BY DATE(data_ora)
            ORDER BY d ASC
            """
        )
        daily = normalize_rows(cur.fetchall() or [])

        cur.execute(
            """
            SELECT f.id AS faq_id, f.domanda AS domanda, COUNT(*) AS n_down
            FROM feedback b
            JOIN faq f ON f.id = b.faq_id
            WHERE b.value=-1 AND b.created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
            GROUP BY f.id
            ORDER BY n_down DESC
            LIMIT 8
            """
        )
        top_bad = normalize_rows(cur.fetchall() or [])

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
            fb_total=fb_total,
            fb_up=fb_up,
            fb_down=fb_down,
            fb_rate=fb_rate,
            top_bad=top_bad,
        )

    @app.get("/admin/faqs")
    def admin_faqs():
        redirect_response = admin_required()
        if redirect_response:
            return redirect_response

        conn = get_connection()
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT id, categoria, domanda, data_aggiornamento FROM faq ORDER BY id DESC")
        rows = cur.fetchall() or []
        cur.close()
        conn.close()

        for row in rows:
            question = (row.get("domanda") or "").strip()
            row["domanda_short"] = (question[:90] + "…") if len(question) > 90 else question

        return render_template("admin_faqs.html", rows=rows)

    @app.get("/admin/faqs/new")
    def admin_faq_new():
        redirect_response = admin_required()
        if redirect_response:
            return redirect_response

        return render_template(
            "admin_faq_form.html",
            heading="Nuova FAQ",
            form_action="/admin/faqs/new",
            faq=None,
            error=None,
        )

    @app.post("/admin/faqs/new")
    def admin_faq_new_post():
        redirect_response = admin_required()
        if redirect_response:
            return redirect_response

        categoria = (request.form.get("categoria") or "generale").strip()[:100] or "generale"
        domanda = (request.form.get("domanda") or "").strip()
        risposta1 = (request.form.get("risposta1") or "").strip()
        risposta2 = (request.form.get("risposta2") or "").strip()
        risposta3 = (request.form.get("risposta3") or "").strip()

        if not domanda or not risposta1:
            return render_template(
                "admin_faq_form.html",
                heading="Nuova FAQ",
                form_action="/admin/faqs/new",
                faq={
                    "categoria": categoria,
                    "domanda": domanda,
                    "risposta1": risposta1,
                    "risposta2": risposta2,
                    "risposta3": risposta3,
                },
                error="Domanda e Risposta 1 sono obbligatorie.",
            )

        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO faq (categoria, domanda, risposta1, risposta2, risposta3) VALUES (%s, %s, %s, %s, %s)",
            (categoria, domanda, risposta1, risposta2 or None, risposta3 or None),
        )
        conn.commit()
        cur.close()
        conn.close()

        return redirect("/admin/faqs")

    @app.get("/admin/faqs/edit/<int:faq_id>")
    def admin_faq_edit(faq_id: int):
        redirect_response = admin_required()
        if redirect_response:
            return redirect_response

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
        redirect_response = admin_required()
        if redirect_response:
            return redirect_response

        categoria = (request.form.get("categoria") or "generale").strip()[:100] or "generale"
        domanda = (request.form.get("domanda") or "").strip()
        risposta1 = (request.form.get("risposta1") or "").strip()
        risposta2 = (request.form.get("risposta2") or "").strip()
        risposta3 = (request.form.get("risposta3") or "").strip()

        if not domanda or not risposta1:
            return render_template(
                "admin_faq_form.html",
                heading=f"Modifica FAQ #{faq_id}",
                form_action=f"/admin/faqs/edit/{faq_id}",
                faq={
                    "id": faq_id,
                    "categoria": categoria,
                    "domanda": domanda,
                    "risposta1": risposta1,
                    "risposta2": risposta2,
                    "risposta3": risposta3,
                },
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
            (categoria, domanda, risposta1, risposta2 or None, risposta3 or None, int(faq_id)),
        )
        conn.commit()
        cur.close()
        conn.close()

        return redirect("/admin/faqs")

    @app.post("/admin/faqs/delete/<int:faq_id>")
    def admin_faq_delete(faq_id: int):
        redirect_response = admin_required()
        if redirect_response:
            return redirect_response

        conn = get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM faq WHERE id=%s", (int(faq_id),))
        conn.commit()
        cur.close()
        conn.close()

        return redirect("/admin/faqs")


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=app.config["PORT"], debug=app.config["DEBUG"])
