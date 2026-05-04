
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║   DATABASE — Sistema de Atendimentos Samsung SMB                            ║
║   SQLite | Atendimentos + Pagamentos + Vendedores                           ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import sqlite3
import os
from datetime import datetime
from google_sheets_sync import sync_to_sheets

import os
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "atendimentos.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    # Ativa o modo WAL (Write-Ahead Logging) para melhor performance e segurança em concorrência
    conn.execute("PRAGMA journal_mode=WAL")
    # Aumenta a segurança de escrita
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    cur = conn.cursor()

    # ── Tabela atendimentos ──────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS atendimentos (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            atendente           TEXT    NOT NULL,
            data_atendimento    TEXT    NOT NULL,
            numero_pedido       TEXT    NOT NULL UNIQUE,
            nome_cliente        TEXT    NOT NULL,
            valor_pedido        REAL    NOT NULL DEFAULT 0.0,
            arquivo_comprovante TEXT    DEFAULT '',
            data_hora_registro  TEXT    DEFAULT ''
        )
    """)

    # ── Tabela pagamentos ────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS pagamentos (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            numero_os           TEXT    NOT NULL,
            atendente           TEXT    DEFAULT '',
            data_pagamento      TEXT    DEFAULT '',
            nome_cliente        TEXT    DEFAULT '',
            valor_produto       REAL    DEFAULT 0.0,
            valor_entrada       REAL    DEFAULT 0.0,
            valor_saldo         REAL    DEFAULT 0.0,
            tipo_pagamento      TEXT    DEFAULT '',
            arquivo_comprovante TEXT    DEFAULT '',
            data_hora_registro  TEXT    DEFAULT ''
        )
    """)

    # ── Tabela vendedores ────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS vendedores (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            nome       TEXT    NOT NULL UNIQUE,
            criado_em  TEXT    DEFAULT ''
        )
    """)

    # ── Migração: adiciona colunas faltantes em bancos antigos ───────────────
    _migrar_colunas(cur)

    conn.commit()
    conn.close()


def _migrar_colunas(cur):
    """Adiciona colunas novas sem quebrar bancos de dados existentes."""

    def colunas_de(tabela):
        cur.execute(f"PRAGMA table_info({tabela})")
        return [row[1] for row in cur.fetchall()]

    # atendimentos
    cols_at = colunas_de("atendimentos")
    for col, defi in [
        ("arquivo_comprovante", "TEXT DEFAULT ''"),
        ("data_hora_registro",  "TEXT DEFAULT ''"),
    ]:
        if col not in cols_at:
            cur.execute(f"ALTER TABLE atendimentos ADD COLUMN {col} {defi}")

    # pagamentos
    cols_pag = colunas_de("pagamentos")
    for col, defi in [
        ("atendente",           "TEXT DEFAULT ''"),
        ("data_pagamento",      "TEXT DEFAULT ''"),
        ("nome_cliente",        "TEXT DEFAULT ''"),
        ("valor_produto",       "REAL DEFAULT 0.0"),
        ("valor_entrada",       "REAL DEFAULT 0.0"),
        ("valor_saldo",         "REAL DEFAULT 0.0"),
        ("tipo_pagamento",      "TEXT DEFAULT ''"),
        ("arquivo_comprovante", "TEXT DEFAULT ''"),
        ("data_hora_registro",  "TEXT DEFAULT ''"),
    ]:
        if col not in cols_pag:
            cur.execute(f"ALTER TABLE pagamentos ADD COLUMN {col} {defi}")

    # vendedores
    cols_vend = colunas_de("vendedores")
    for col, defi in [
        ("criado_em", "TEXT DEFAULT ''"),
    ]:
        if col not in cols_vend:
            cur.execute(f"ALTER TABLE vendedores ADD COLUMN {col} {defi}")


# Inicializa o banco ao importar
init_db()


# ═══════════════════════════════════════════════════════════════════════════════
# ATENDIMENTOS
# ═══════════════════════════════════════════════════════════════════════════════

def salvar_atendimento(dados: dict):
    conn = get_conn()
    try:
        cursor = conn.execute("""
            INSERT INTO atendimentos
                (atendente, data_atendimento, numero_pedido, nome_cliente,
                 valor_pedido, arquivo_comprovante, data_hora_registro)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            dados["atendente"],
            dados["data_atendimento"],
            dados["numero_pedido"],
            dados["nome_cliente"],
            dados["valor_pedido"],
            dados.get("arquivo_comprovante", ""),
            dados.get("data_hora_registro", datetime.now().strftime("%d/%m/%Y %H:%M:%S")),
        ))
        conn.commit()
        
        # Sincronizar com Google Sheets
        novo_id = cursor.lastrowid
        dados_sync = dados.copy()
        dados_sync["id"] = novo_id
        sync_to_sheets("atendimentos", dados_sync)
        
    except sqlite3.IntegrityError:
        raise ValueError(f"Número de pedido '{dados['numero_pedido']}' já cadastrado.")
    finally:
        conn.close()


def carregar_atendimentos() -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM atendimentos ORDER BY id DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def contar_atendimentos() -> int:
    conn = get_conn()
    count = conn.execute("SELECT COUNT(*) FROM atendimentos").fetchone()[0]
    conn.close()
    return count


def obter_valor_total() -> float:
    conn = get_conn()
    total = conn.execute("SELECT COALESCE(SUM(valor_pedido), 0) FROM atendimentos").fetchone()[0]
    conn.close()
    return float(total)


def atualizar_atendimento(id_: int, dados: dict):
    conn = get_conn()
    conn.execute("""
        UPDATE atendimentos
        SET atendente=?, data_atendimento=?, numero_pedido=?,
            nome_cliente=?, valor_pedido=?
        WHERE id=?
    """, (
        dados["atendente"],
        dados["data_atendimento"],
        dados["numero_pedido"],
        dados["nome_cliente"],
        dados["valor_pedido"],
        id_,
    ))
    conn.commit()
    conn.close()


def limpar_todos_dados():
    conn = get_conn()
    conn.execute("DELETE FROM atendimentos")
    conn.commit()
    conn.close()


def estatisticas_por_atendente() -> list[dict]:
    conn = get_conn()
    rows = conn.execute("""
        SELECT
            atendente,
            COUNT(*)        AS total_atendimentos,
            SUM(valor_pedido) AS valor_total,
            AVG(valor_pedido) AS valor_medio
        FROM atendimentos
        GROUP BY atendente
        ORDER BY valor_total DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def estatisticas_por_periodo() -> list[dict]:
    conn = get_conn()
    rows = conn.execute("""
        SELECT
            data_atendimento       AS periodo,
            COUNT(*)               AS total,
            SUM(valor_pedido)      AS valor_total
        FROM atendimentos
        GROUP BY data_atendimento
        ORDER BY data_atendimento DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def evolucao_por_vendedor() -> list[dict]:
    conn = get_conn()
    rows = conn.execute("""
        SELECT
            atendente,
            data_atendimento AS data,
            SUM(valor_pedido) AS valor_total
        FROM atendimentos
        GROUP BY atendente, data_atendimento
        ORDER BY data_atendimento
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ═══════════════════════════════════════════════════════════════════════════════
# PAGAMENTOS
# ═══════════════════════════════════════════════════════════════════════════════

def salvar_pagamento(dados: dict):
    conn = get_conn()
    try:
        cursor = conn.execute("""
            INSERT INTO pagamentos
                (numero_os, atendente, data_pagamento, nome_cliente,
                 valor_produto, valor_entrada, valor_saldo,
                 tipo_pagamento, arquivo_comprovante, data_hora_registro)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            dados["numero_os"],
            dados.get("atendente", ""),
            dados.get("data_pagamento", ""),
            dados.get("nome_cliente", ""),
            dados.get("valor_produto", 0.0),
            dados.get("valor_entrada", 0.0),
            dados.get("valor_saldo", 0.0),
            dados.get("tipo_pagamento", ""),
            dados.get("arquivo_comprovante", ""),
            dados.get("data_hora_registro", datetime.now().strftime("%d/%m/%Y %H:%M:%S")),
        ))
        conn.commit()
        
        # Sincronizar com Google Sheets
        novo_id = cursor.lastrowid
        dados_sync = dados.copy()
        dados_sync["id"] = novo_id
        sync_to_sheets("pagamentos", dados_sync)
        
    finally:
        conn.close()


def carregar_pagamentos() -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM pagamentos ORDER BY id DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def contar_pagamentos() -> int:
    conn = get_conn()
    count = conn.execute("SELECT COUNT(*) FROM pagamentos").fetchone()[0]
    conn.close()
    return count


def atualizar_pagamento(id_: int, dados: dict):
    conn = get_conn()
    conn.execute("""
        UPDATE pagamentos
        SET numero_os=?, atendente=?, data_pagamento=?, nome_cliente=?,
            valor_produto=?, valor_entrada=?, valor_saldo=?, tipo_pagamento=?
        WHERE id=?
    """, (
        dados["numero_os"],
        dados.get("atendente", ""),
        dados.get("data_pagamento", ""),
        dados.get("nome_cliente", ""),
        dados.get("valor_produto", 0.0),
        dados.get("valor_entrada", 0.0),
        dados.get("valor_saldo", 0.0),
        dados.get("tipo_pagamento", ""),
        id_,
    ))
    conn.commit()
    conn.close()


def excluir_pagamento(id_: int):
    conn = get_conn()
    conn.execute("DELETE FROM pagamentos WHERE id=?", (id_,))
    conn.commit()
    conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
# VENDEDORES
# ═══════════════════════════════════════════════════════════════════════════════

def listar_vendedores() -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM vendedores ORDER BY nome"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def cadastrar_vendedor(nome: str):
    conn = get_conn()
    try:
        conn.execute("""
            INSERT INTO vendedores (nome, criado_em)
            VALUES (?, ?)
        """, (nome, datetime.now().strftime("%d/%m/%Y %H:%M:%S")))
        conn.commit()
    except sqlite3.IntegrityError:
        raise ValueError(f"Vendedor '{nome}' já cadastrado.")
    finally:
        conn.close()


def excluir_vendedor(id_: int):
    conn = get_conn()
    conn.execute("DELETE FROM vendedores WHERE id=?", (id_,))
    conn.commit()
    conn.close()