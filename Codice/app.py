from __future__ import annotations

import os
import random
from datetime import timedelta
from typing import Dict

import mysql.connector
from mysql.connector import Error as MySQLError
from dotenv import load_dotenv
from flask import (
    Flask,
    jsonify,
    redirect,
    render_template_string,
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
        # se non hai permessi su information_schema, meglio non rompere tutto:
        exists = False

    _SCHEMA_CACHE[key][column] = bool(exists)
    return bool(exists)


def admin_required():
    if not session.get("admin_user_id"):
        return redirect(url_for("admin_login"))
    return None


def insert_log_message(user_msg: str, reply: str, best_score: float, matched_id):
    """
    Inserisce SEMPRE similarity/faq_id/resolved se le colonne esistono.
    Non dipende da information_schema (che può essere bloccato).
    Fa fallback automatico se schema vecchio.
    """
    try:
        conn = get_connection()
        cur = conn.cursor()

        resolved = 1 if matched_id else 0
        faq_id_val = matched_id  # può essere None

        # 1) tentativo con schema nuovo
        try:
            cur.execute(
                "INSERT INTO logs (user_id, messaggio_utente, risposta_bot, similarity, faq_id, resolved) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (None, user_msg, reply, round(float(best_score), 6), faq_id_val, resolved),
            )
            conn.commit()
            cur.close()
            conn.close()
            return
        except MySQLError as e:
            # se mancano colonne nello schema, fallback
            msg = str(e).lower()
            if ("unknown column" in msg) or ("has no default" in msg) or ("doesn't have a default" in msg):
                conn.rollback()
            else:
                # altri errori: riprovo comunque col fallback, ma non blocco l'utente
                try:
                    conn.rollback()
                except Exception:
                    pass

        # 2) fallback schema vecchio
        try:
            cur.execute(
                "INSERT INTO logs (user_id, messaggio_utente, risposta_bot) VALUES (%s, %s, %s)",
                (None, user_msg, reply),
            )
            conn.commit()
        finally:
            cur.close()
            conn.close()

    except Exception:
        # Non blocco il cliente se logging fallisce
        pass


# =========================
# Public routes
# =========================
@app.get("/")
def site_home():
    # Sito principale + UI chat
    return send_from_directory(STATIC_DIR, "index.html")


@app.get("/health")
def health():
    return jsonify({"ok": True})


@app.post("/message")
def message():
    data = request.get_json(silent=True) or {}
    user_msg = (data.get("message") or "").strip()

    if user_msg == "":
        return jsonify({"reply": "Non ho ricevuto alcun messaggio.", "faq_matched_id": None})

    # Prendo tutte le FAQ
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT id, domanda, risposta1, risposta2, risposta3 FROM faq")
    faqs = cur.fetchall()
    cur.close()
    conn.close()

    if not faqs:
        return jsonify({"reply": "Al momento non ho contenuti disponibili.", "faq_matched_id": None})

    domande_pulite = [clean_text(row["domanda"]) for row in faqs]
    user_clean = clean_text(user_msg)

    if user_clean == "":
        return jsonify({"reply": "Puoi riformulare con più dettagli?", "faq_matched_id": None})

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

    # ✅ Salvo log (ora inserisce davvero similarity/faq_id/resolved quando esistono)
    insert_log_message(user_msg=user_msg, reply=reply, best_score=best_score, matched_id=matched_id)

    return jsonify(
        {
            "reply": reply,
            "faq_matched_id": matched_id,
            "similarity": round(best_score, 3),
        }
    )


# =========================
# Admin UI (server-rendered)
# =========================
ADMIN_BASE_HTML = r"""
<!doctype html>
<html lang="it">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>{{ title }}</title>
  <link rel="stylesheet" href="/static/admin.css" />
</head>
<body>
  <header class="admin-topbar">
    <div class="admin-topbar-inner">
      <div class="admin-brand">
        <span class="admin-dot"></span>
        <strong>Utixo Copilot</strong>
        <span class="admin-badge">Admin</span>
      </div>
      <nav class="admin-nav">
        <a href="/admin">Report</a>
        <a href="/admin/faqs">FAQ</a>
        <a href="/admin/logout" class="admin-nav-danger">Logout</a>
      </nav>
    </div>
  </header>

  <main class="admin-main">
    {{ content | safe }}
  </main>

  <script src="/static/admin.js" defer></script>
</body>
</html>
"""

LOGIN_HTML = r"""
<!doctype html>
<html lang="it">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>Login Admin - Utixo Copilot</title>
  <link rel="stylesheet" href="/static/admin.css" />
</head>
<body class="admin-login-body">
  <div class="admin-login-card">
    <h1>Admin Login</h1>
    <p class="admin-muted">Accedi per gestire FAQ e report.</p>

    {% if error %}
      <div class="admin-alert">{{ error }}</div>
    {% endif %}

    <form method="post" class="admin-form">
      <label>Nome utente</label>
      <input name="username" autocomplete="username" required />

      <label>Password</label>
      <input name="password" type="password" autocomplete="current-password" required />

      <button type="submit" class="admin-btn-primary">Accedi</button>
    </form>

    <div class="admin-footnote">Utixo Copilot • Pannello amministrazione</div>
  </div>
</body>
</html>
"""


@app.get("/admin/login")
def admin_login():
    if session.get("admin_user_id"):
        return redirect(url_for("admin_dashboard"))
    return render_template_string(LOGIN_HTML, error=None)


@app.post("/admin/login")
def admin_login_post():
    username = (request.form.get("username") or "").strip()
    password = (request.form.get("password") or "").strip()

    if not username or not password:
        return render_template_string(LOGIN_HTML, error="Inserisci username e password.")

    # ✅ Login su tabella "utenti" con SHA256 lato DB:
    #    password in DB = SHA2('plain', 256)
    conn = get_connection()
    cur = conn.cursor(dictionary=True)

    cur.execute(
        """
        SELECT id, nome, email
        FROM utenti
        WHERE nome = %s
          AND password = SHA2(%s, 256)
        LIMIT 1
        """,
        (username, password),
    )
    row = cur.fetchone()

    cur.close()
    conn.close()

    if not row:
        return render_template_string(LOGIN_HTML, error="Credenziali non valide.")

    session.permanent = True
    session["admin_user_id"] = int(row["id"])
    session["admin_username"] = row.get("nome") or username
    session["admin_email"] = row.get("email") or ""  # ✅ era "mail"
    return redirect(url_for("admin_dashboard"))


@app.get("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("admin_login"))


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
    logs_count = int(cur.fetchone()["c"])

    has_resolved = _has_column(conn, "logs", "resolved")
    has_similarity = _has_column(conn, "logs", "similarity")

    resolved_count = None
    unresolved_count = None
    if has_resolved:
        cur.execute("SELECT COUNT(*) AS c FROM logs WHERE resolved=1")
        resolved_count = int(cur.fetchone()["c"])
        cur.execute("SELECT COUNT(*) AS c FROM logs WHERE resolved=0")
        unresolved_count = int(cur.fetchone()["c"])

    # ultimi log
    if has_similarity:
        cur.execute(
            "SELECT data_ora, messaggio_utente, risposta_bot, similarity, "
            + ("resolved " if has_resolved else "NULL AS resolved ")
            + "FROM logs ORDER BY id DESC LIMIT 20"
        )
    else:
        cur.execute(
            "SELECT data_ora, messaggio_utente, risposta_bot, NULL AS similarity, "
            + ("resolved " if has_resolved else "NULL AS resolved ")
            + "FROM logs ORDER BY id DESC LIMIT 20"
        )
    latest = cur.fetchall()

    cur.close()
    conn.close()

    cards = []
    cards.append(f"""
      <div class="admin-card">
        <div class="admin-kpi">
          <div>
            <div class="admin-kpi-label">FAQ totali</div>
            <div class="admin-kpi-value">{faq_count}</div>
          </div>
        </div>
      </div>
    """)
    cards.append(f"""
      <div class="admin-card">
        <div class="admin-kpi">
          <div>
            <div class="admin-kpi-label">Messaggi ricevuti</div>
            <div class="admin-kpi-value">{logs_count}</div>
          </div>
        </div>
      </div>
    """)
    if resolved_count is not None and unresolved_count is not None:
        cards.append(f"""
          <div class="admin-card">
            <div class="admin-kpi">
              <div>
                <div class="admin-kpi-label">Risposte trovate</div>
                <div class="admin-kpi-value">{resolved_count}</div>
              </div>
            </div>
          </div>
        """)
        cards.append(f"""
          <div class="admin-card">
            <div class="admin-kpi">
              <div>
                <div class="admin-kpi-label">Non risolte</div>
                <div class="admin-kpi-value">{unresolved_count}</div>
              </div>
            </div>
          </div>
        """)

    rows_html = ""
    for r in latest:
        dt = str(r.get("data_ora") or "")
        msg = (r.get("messaggio_utente") or "")[:140]
        rep = (r.get("risposta_bot") or "")[:140]
        simv = r.get("similarity")
        sim_txt = f"{float(simv):.3f}" if simv is not None else "-"
        resv = r.get("resolved")
        badge = ""
        if resv is not None:
            badge = '<span class="pill ok">OK</span>' if int(resv) == 1 else '<span class="pill warn">NO</span>'
        rows_html += f"""
          <tr>
            <td class="mono">{dt}</td>
            <td>{msg}</td>
            <td>{rep}</td>
            <td class="mono">{sim_txt}</td>
            <td>{badge}</td>
          </tr>
        """

    content = f"""
      <h1>Report</h1>
      <p class="admin-muted">Panoramica su FAQ e richieste ricevute.</p>

      <div class="admin-grid">
        {''.join(cards)}
      </div>

      <div class="admin-card admin-card-wide">
        <div class="admin-card-title">Ultimi messaggi</div>
        <div class="admin-table-wrap">
          <table class="admin-table">
            <thead>
              <tr>
                <th>Data</th>
                <th>Messaggio utente</th>
                <th>Risposta bot</th>
                <th>Sim</th>
                <th>Esito</th>
              </tr>
            </thead>
            <tbody>
              {rows_html if rows_html else '<tr><td colspan="5" class="admin-muted">Nessun log disponibile.</td></tr>'}
            </tbody>
          </table>
        </div>
      </div>
    """
    return render_template_string(ADMIN_BASE_HTML, title="Admin • Report", content=content)


@app.get("/admin/faqs")
def admin_faqs():
    redir = admin_required()
    if redir:
        return redir

    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT id, categoria, domanda, risposta1, risposta2, risposta3 FROM faq ORDER BY id DESC")
    faqs = cur.fetchall()
    cur.close()
    conn.close()

    table_rows = ""
    for f in faqs:
        fid = int(f["id"])
        cat = (f.get("categoria") or "generale")
        dom = (f.get("domanda") or "")[:120]
        table_rows += f"""
        <tr>
          <td class="mono">{fid}</td>
          <td>{cat}</td>
          <td>{dom}</td>
          <td class="admin-actions">
            <button class="admin-btn" data-edit="{fid}">Modifica</button>
          </td>
        </tr>
        """

    content = f"""
      <h1>FAQ</h1>
      <p class="admin-muted">Aggiungi e modifica le risposte del Copilot.</p>

      <div class="admin-split">
        <div class="admin-card">
          <div class="admin-card-title">Aggiungi FAQ</div>
          <form method="post" action="/admin/faqs/new" class="admin-form">
            <label>Categoria</label>
            <input name="categoria" placeholder="es. Microsoft 365" />

            <label>Domanda</label>
            <textarea name="domanda" rows="3" required placeholder="Scrivi la domanda (come la farebbe un cliente)"></textarea>

            <label>Risposta 1</label>
            <textarea name="risposta1" rows="3" required placeholder="Risposta principale"></textarea>

            <label>Risposta 2 (opzionale)</label>
            <textarea name="risposta2" rows="3" placeholder="Variante risposta"></textarea>

            <label>Risposta 3 (opzionale)</label>
            <textarea name="risposta3" rows="3" placeholder="Variante risposta"></textarea>

            <button type="submit" class="admin-btn-primary">Salva FAQ</button>
          </form>
        </div>

        <div class="admin-card">
          <div class="admin-card-title">Elenco FAQ</div>
          <div class="admin-table-wrap">
            <table class="admin-table" id="faqTable">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Categoria</th>
                  <th>Domanda</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {table_rows if table_rows else '<tr><td colspan="4" class="admin-muted">Nessuna FAQ trovata.</td></tr>'}
              </tbody>
            </table>
          </div>
          <div class="admin-hint">Clicca “Modifica” per aggiornare una FAQ.</div>
        </div>
      </div>

      <!-- Modal edit -->
      <div class="admin-modal" id="editModal" aria-hidden="true">
        <div class="admin-modal-card">
          <div class="admin-modal-head">
            <strong>Modifica FAQ</strong>
            <button class="admin-icon" id="closeModal" aria-label="Chiudi">✕</button>
          </div>
          <form method="post" id="editForm" action="/admin/faqs/update" class="admin-form admin-form-compact">
            <input type="hidden" name="id" id="edit_id" />
            <label>Categoria</label>
            <input name="categoria" id="edit_categoria" />

            <label>Domanda</label>
            <textarea name="domanda" id="edit_domanda" rows="3" required></textarea>

            <label>Risposta 1</label>
            <textarea name="risposta1" id="edit_risposta1" rows="3" required></textarea>

            <label>Risposta 2</label>
            <textarea name="risposta2" id="edit_risposta2" rows="3"></textarea>

            <label>Risposta 3</label>
            <textarea name="risposta3" id="edit_risposta3" rows="3"></textarea>

            <button type="submit" class="admin-btn-primary">Salva modifiche</button>
          </form>
        </div>
      </div>
    """
    return render_template_string(ADMIN_BASE_HTML, title="Admin • FAQ", content=content)


@app.post("/admin/faqs/new")
def admin_faqs_new():
    redir = admin_required()
    if redir:
        return redir

    categoria = (request.form.get("categoria") or "generale").strip() or "generale"
    domanda = (request.form.get("domanda") or "").strip()
    risposta1 = (request.form.get("risposta1") or "").strip()
    risposta2 = (request.form.get("risposta2") or "").strip() or None
    risposta3 = (request.form.get("risposta3") or "").strip() or None

    if not domanda or not risposta1:
        return redirect(url_for("admin_faqs"))

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


@app.get("/admin/faqs/<int:faq_id>")
def admin_faq_get(faq_id: int):
    redir = admin_required()
    if redir:
        return redir

    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT id, categoria, domanda, risposta1, risposta2, risposta3 FROM faq WHERE id=%s", (faq_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row:
        return jsonify({"ok": False, "error": "FAQ non trovata"}), 404

    return jsonify({"ok": True, "faq": row})


@app.post("/admin/faqs/update")
def admin_faq_update():
    redir = admin_required()
    if redir:
        return redir

    faq_id = int(request.form.get("id") or 0)
    categoria = (request.form.get("categoria") or "generale").strip() or "generale"
    domanda = (request.form.get("domanda") or "").strip()
    risposta1 = (request.form.get("risposta1") or "").strip()
    risposta2 = (request.form.get("risposta2") or "").strip() or None
    risposta3 = (request.form.get("risposta3") or "").strip() or None

    if faq_id <= 0 or not domanda or not risposta1:
        return redirect(url_for("admin_faqs"))

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE faq SET categoria=%s, domanda=%s, risposta1=%s, risposta2=%s, risposta3=%s WHERE id=%s",
        (categoria, domanda, risposta1, risposta2, risposta3, faq_id),
    )
    conn.commit()
    cur.close()
    conn.close()

    return redirect(url_for("admin_faqs"))


# Static files
@app.get("/static/<path:filename>")
def static_files(filename: str):
    return send_from_directory(STATIC_DIR, filename)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=True)