from collections.abc import Sequence

import mysql.connector
from config import cfg


_Params = tuple | dict | Sequence | None


def get_connection():
    return mysql.connector.connect(**cfg.db_conn_params)


def query_all(sql: str, params: _Params = ()):
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(sql, params)
        return cursor.fetchall()
    finally:
        conn.close()


def query_one(sql: str, params: _Params = ()):
    rows = query_all(sql, params)
    return rows[0] if rows else None
