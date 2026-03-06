from __future__ import annotations

import mysql.connector
from flask import current_app



def get_connection():
    return mysql.connector.connect(
        host=current_app.config["DB_HOST"],
        user=current_app.config["DB_USER"],
        password=current_app.config["DB_PASSWORD"],
        database=current_app.config["DB_NAME"],
        port=current_app.config["DB_PORT"],
    )



def table_has_column(conn, table: str, column: str) -> bool:
    cur = conn.cursor()
    cur.execute(
        """
        SELECT COUNT(*)
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s AND COLUMN_NAME=%s
        """,
        (current_app.config["DB_NAME"], table, column),
    )
    ok = (cur.fetchone() or [0])[0] > 0
    cur.close()
    return bool(ok)
