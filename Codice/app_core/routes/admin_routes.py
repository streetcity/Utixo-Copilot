from __future__ import annotations

from flask import Blueprint, current_app, redirect, render_template, request, session, url_for

from ..db import get_connection
from ..services.auth_service import check_password_and_upgrade
from ..services.conversation_service import normalize_rows

admin_bp = Blueprint("admin", __name__)



def admin_required():
    if not session.get("admin_user_id"):
        return redirect(url_for("admin.admin_login"))
    return None


@admin_bp.get("/admin/login")
def admin_login():
    if session.get("admin_user_id"):
        return redirect(url_for("admin.admin_dashboard"))
    return render_template("admin_login.html", error=None)


@admin_bp.post("/admin/login")
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
    return redirect(url_for("admin.admin_dashboard"))


@admin_bp.get("/admin/logout")
def admin_logout():
    session.pop("admin_user_id", None)
    session.pop("admin_username", None)
    return redirect(url_for("admin.admin_login"))


@admin_bp.get("/admin")
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


@admin_bp.get("/admin/faqs")
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


@admin_bp.get("/admin/faqs/new")
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


@admin_bp.post("/admin/faqs/new")
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


@admin_bp.get("/admin/faqs/edit/<int:faq_id>")
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


@admin_bp.post("/admin/faqs/edit/<int:faq_id>")
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


@admin_bp.post("/admin/faqs/delete/<int:faq_id>")
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
