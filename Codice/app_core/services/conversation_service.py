from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from ..db import get_connection



def _dt_to_str(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, date):
        return value.strftime("%Y-%m-%d")
    return value



def normalize_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    output: List[Dict[str, Any]] = []
    for row in rows or []:
        output.append({k: _dt_to_str(v) for k, v in (row or {}).items()})
    return output



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
    return {k: _dt_to_str(v) for k, v in row.items()}



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
        row = {k: _dt_to_str(v) for k, v in (row or {}).items()}
        ts = row.get("data_ora")
        user_text = (row.get("messaggio_utente") or "").strip()
        if user_text:
            messages.append({"role": "user", "content": user_text, "created_at": ts})
        bot_text = (row.get("risposta_bot") or "").strip()
        if bot_text:
            messages.append({"role": "assistant", "content": bot_text, "created_at": ts})
    return messages
