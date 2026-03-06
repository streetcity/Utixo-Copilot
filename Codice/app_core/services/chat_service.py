from __future__ import annotations

from typing import Optional

from flask import current_app, jsonify

from ..db import get_connection
from ..utils.text_utils import humanize_answer
from .conversation_service import (
    create_conversation,
    ensure_conversation_belongs,
    set_conversation_title,
    touch_conversation,
)
from .faq_service import match_faq



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
        return jsonify({
            "ok": True,
            "reply": "Scrivi un messaggio valido.",
            "faq_matched_id": None,
            "conversation_id": conversation_id,
        })

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
        reply = humanize_answer(user_msg, reply)

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
