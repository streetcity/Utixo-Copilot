from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request, send_from_directory, session

from ..db import get_connection
from ..services.auth_service import (
    check_password_and_upgrade,
    clear_user_session,
    current_user,
    hash_password_new,
    set_user_session,
)
from ..services.chat_service import handle_chat
from ..services.conversation_service import (
    create_conversation,
    get_conversation,
    get_messages,
    list_conversations_for_user,
)

public_bp = Blueprint("public", __name__)


@public_bp.get("/")
def home():
    return send_from_directory(current_app.config["STATIC_DIR"], "index.html")


@public_bp.get("/static/<path:filename>")
def static_files(filename: str):
    return send_from_directory(current_app.config["STATIC_DIR"], filename)


@public_bp.get("/favicon.ico")
def favicon():
    try:
        return send_from_directory(current_app.config["STATIC_DIR"], "favicon.ico")
    except Exception:
        return ("", 204)


@public_bp.get("/me")
def me():
    return jsonify({"user": current_user()})


@public_bp.get("/auth/me")
def auth_me_alias():
    return me()


@public_bp.post("/auth/register")
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


@public_bp.post("/auth/login")
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


@public_bp.post("/auth/logout")
def logout():
    clear_user_session()
    session.pop("admin_user_id", None)
    session.pop("admin_username", None)
    return jsonify({"ok": True})


@public_bp.get("/conversations")
def list_conversations_legacy():
    user = current_user()
    if not user:
        return jsonify({"ok": True, "conversations": []})
    return jsonify({"ok": True, "conversations": list_conversations_for_user(int(user["id"]))})


@public_bp.get("/conversations/<int:conversation_id>/messages")
def conversation_messages_legacy(conversation_id: int):
    user = current_user()
    if not user:
        return jsonify({"ok": False, "error": "Non autorizzato"}), 401

    try:
        rows = get_messages(int(user["id"]), int(conversation_id))
    except PermissionError:
        return jsonify({"ok": False, "error": "Non autorizzato"}), 403

    return jsonify({"ok": True, "messages": rows})


@public_bp.get("/api/conversations")
def api_list_conversations():
    user = current_user()
    if not user:
        return jsonify({"ok": True, "conversations": []})
    return jsonify({"ok": True, "conversations": list_conversations_for_user(int(user["id"]))})


@public_bp.post("/api/conversations")
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


@public_bp.get("/api/conversations/<int:conversation_id>")
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


@public_bp.get("/api/conversations/<int:conversation_id>/messages")
def api_get_messages(conversation_id: int):
    user = current_user()
    if not user:
        return jsonify({"ok": False, "error": "Non autorizzato"}), 401

    try:
        rows = get_messages(int(user["id"]), int(conversation_id))
    except PermissionError:
        return jsonify({"ok": False, "error": "Non autorizzato"}), 403

    return jsonify({"ok": True, "messages": rows})


@public_bp.post("/api/conversations/<int:conversation_id>/messages")
def api_post_message(conversation_id: int):
    user = current_user()
    if not user:
        return jsonify({"ok": False, "error": "Non autorizzato"}), 401

    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()
    if not message:
        return jsonify({"ok": False, "error": "Messaggio vuoto"}), 400

    return handle_chat(message, int(user["id"]), int(conversation_id))


@public_bp.post("/chat")
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


@public_bp.post("/ask")
def ask_alias():
    return chat()


@public_bp.post("/feedback")
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
        conn.close()
    except Exception:
        try:
            conn.close()
        except Exception:
            pass
        return jsonify({"ok": False, "error": "impossibile salvare feedback"}), 500

    return jsonify({"ok": True})
