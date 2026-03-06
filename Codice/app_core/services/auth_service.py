from __future__ import annotations

import hashlib
import re
from typing import Any, Dict, Optional

from flask import session



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
