"""
╔══════════════════════════════════════════════════════════════════════════════╗
║   MÓDULO DE NOTIFICAÇÕES — Sistema de Atendimentos Samsung SMB              ║
║   Gerencia notificações por e-mail, SMS e histórico em banco de dados       ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import sqlite3
from datetime import datetime
from typing import Optional
import streamlit as st

DB_PATH = "atendimentos.db"


def get_conn():
    """Obtém conexão com o banco de dados."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_notifications_table():
    """Inicializa a tabela de notificações no banco de dados."""
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS notificacoes (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo                TEXT    NOT NULL,
            destinatario        TEXT    NOT NULL,
            assunto             TEXT    DEFAULT '',
            mensagem            TEXT    DEFAULT '',
            status              TEXT    DEFAULT 'enviada',
            data_hora_envio     TEXT    DEFAULT '',
            referencia_id       INTEGER,
            referencia_tipo     TEXT,
            lido                BOOLEAN DEFAULT 0,
            arquivo_anexo       TEXT    DEFAULT '',
            tipo_anexo          TEXT    DEFAULT ''
        )
    """)

    # Migração: adiciona colunas de anexo se não existirem
    cur.execute("PRAGMA table_info(notificacoes)")
    colunas_existentes = [row[1] for row in cur.fetchall()]

    if "arquivo_anexo" not in colunas_existentes:
        cur.execute("ALTER TABLE notificacoes ADD COLUMN arquivo_anexo TEXT DEFAULT ''")
    if "tipo_anexo" not in colunas_existentes:
        cur.execute("ALTER TABLE notificacoes ADD COLUMN tipo_anexo TEXT DEFAULT ''")

    # Adiciona coluna de preferências de notificação para usuários
    cur.execute("""
        CREATE TABLE IF NOT EXISTS preferencias_notificacao (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario             TEXT    NOT NULL UNIQUE,
            email_atendimento   BOOLEAN DEFAULT 1,
            email_pagamento     BOOLEAN DEFAULT 1,
            notif_sistema       BOOLEAN DEFAULT 1,
            criada_em           TEXT    DEFAULT ''
        )
    """)

    conn.commit()
    conn.close()


# Inicializa a tabela ao importar
init_notifications_table()


# ═══════════════════════════════════════════════════════════════════════════════
# FUNÇÕES DE NOTIFICAÇÃO
# ═══════════════════════════════════════════════════════════════════════════════

def registrar_notificacao(
    tipo: str,
    destinatario: str,
    assunto: str,
    mensagem: str,
    status: str = "enviada",
    referencia_id: Optional[int] = None,
    referencia_tipo: Optional[str] = None,
    arquivo_anexo: Optional[str] = None,
    tipo_anexo: Optional[str] = None,
) -> int:
    """
    Registra uma notificação no banco de dados.

    Parâmetros:
        tipo (str): Tipo de notificação ('email', 'sms', 'sistema')
        destinatario (str): E-mail ou identificador do destinatário
        assunto (str): Assunto da notificação
        mensagem (str): Conteúdo da notificação
        status (str): Status da notificação ('enviada', 'falha', 'pendente')
        referencia_id (int): ID do registro relacionado (atendimento, pagamento)
        referencia_tipo (str): Tipo de referência ('atendimento', 'pagamento')
        arquivo_anexo (str): Nome do arquivo anexado/comprovante
        tipo_anexo (str): Tipo do anexo ('comprovante_pedido', 'comprovante_pagamento')

    Retorna:
        int: ID da notificação registrada
    """
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO notificacoes
                (tipo, destinatario, assunto, mensagem, status, 
                 data_hora_envio, referencia_id, referencia_tipo, arquivo_anexo, tipo_anexo)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            tipo,
            destinatario,
            assunto,
            mensagem,
            status,
            datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            referencia_id,
            referencia_tipo,
            arquivo_anexo or "",
            tipo_anexo or "",
        ))
        conn.commit()
        notif_id = cur.lastrowid
        return notif_id
    finally:
        conn.close()


def carregar_notificacoes(limite: int = 50) -> list[dict]:
    """
    Carrega as notificações mais recentes.

    Parâmetros:
        limite (int): Número máximo de notificações a retornar

    Retorna:
        list[dict]: Lista de notificações
    """
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM notificacoes ORDER BY id DESC LIMIT ?",
        (limite,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def carregar_notificacoes_por_tipo(tipo: str, limite: int = 50) -> list[dict]:
    """
    Carrega notificações filtradas por tipo.

    Parâmetros:
        tipo (str): Tipo de notificação a filtrar
        limite (int): Número máximo de notificações a retornar

    Retorna:
        list[dict]: Lista de notificações do tipo especificado
    """
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM notificacoes WHERE tipo=? ORDER BY id DESC LIMIT ?",
        (tipo, limite)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def contar_notificacoes_nao_lidas() -> int:
    """Conta o número de notificações não lidas."""
    conn = get_conn()
    count = conn.execute(
        "SELECT COUNT(*) FROM notificacoes WHERE lido=0"
    ).fetchone()[0]
    conn.close()
    return count


def marcar_como_lida(notif_id: int):
    """Marca uma notificação como lida."""
    conn = get_conn()
    conn.execute(
        "UPDATE notificacoes SET lido=1 WHERE id=?",
        (notif_id,)
    )
    conn.commit()
    conn.close()


def marcar_todas_como_lidas():
    """Marca todas as notificações como lidas."""
    conn = get_conn()
    conn.execute("UPDATE notificacoes SET lido=1")
    conn.commit()
    conn.close()


def obter_preferencias_notificacao(usuario: str) -> dict:
    """
    Obtém as preferências de notificação de um usuário.

    Parâmetros:
        usuario (str): Nome do usuário

    Retorna:
        dict: Dicionário com as preferências
    """
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM preferencias_notificacao WHERE usuario=?",
        (usuario,)
    ).fetchone()
    conn.close()

    if row:
        return dict(row)
    else:
        # Retorna preferências padrão
        return {
            "usuario": usuario,
            "email_atendimento": True,
            "email_pagamento": True,
            "notif_sistema": True,
        }


def salvar_preferencias_notificacao(usuario: str, prefs: dict):
    """
    Salva as preferências de notificação de um usuário.

    Parâmetros:
        usuario (str): Nome do usuário
        prefs (dict): Dicionário com as preferências
    """
    conn = get_conn()
    try:
        # Tenta atualizar
        conn.execute("""
            UPDATE preferencias_notificacao
            SET email_atendimento=?, email_pagamento=?, notif_sistema=?
            WHERE usuario=?
        """, (
            prefs.get("email_atendimento", True),
            prefs.get("email_pagamento", True),
            prefs.get("notif_sistema", True),
            usuario,
        ))

        # Se nenhuma linha foi atualizada, insere
        if conn.total_changes == 0:
            conn.execute("""
                INSERT INTO preferencias_notificacao
                    (usuario, email_atendimento, email_pagamento, 
                     notif_sistema, criada_em)
                VALUES (?, ?, ?, ?, ?)
            """, (
                usuario,
                prefs.get("email_atendimento", True),
                prefs.get("email_pagamento", True),
                prefs.get("notif_sistema", True),
                datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            ))

        conn.commit()
    finally:
        conn.close()


def limpar_notificacoes_antigas(dias: int = 30):
    """
    Remove notificações mais antigas que o número de dias especificado.

    Parâmetros:
        dias (int): Número de dias para manter
    """
    conn = get_conn()
    # Esta é uma implementação simplificada
    # Em produção, você deveria usar DATE() para comparação correta
    conn.execute("""
        DELETE FROM notificacoes 
        WHERE datetime(data_hora_envio) < datetime('now', '-' || ? || ' days')
    """, (dias,))
    conn.commit()
    conn.close()


def obter_estatisticas_notificacoes() -> dict:
    """Obtém estatísticas sobre as notificações."""
    conn = get_conn()

    total = conn.execute("SELECT COUNT(*) FROM notificacoes").fetchone()[0]
    nao_lidas = conn.execute("SELECT COUNT(*) FROM notificacoes WHERE lido=0").fetchone()[0]
    com_anexo = conn.execute("SELECT COUNT(*) FROM notificacoes WHERE arquivo_anexo != ''").fetchone()[0]

    por_tipo = conn.execute("""
        SELECT tipo, COUNT(*) as total, 
               SUM(CASE WHEN status='enviada' THEN 1 ELSE 0 END) as enviadas,
               SUM(CASE WHEN status='falha' THEN 1 ELSE 0 END) as falhas
        FROM notificacoes
        GROUP BY tipo
    """).fetchall()

    conn.close()

    return {
        "total": total,
        "nao_lidas": nao_lidas,
        "com_anexo": com_anexo,
        "por_tipo": [dict(r) for r in por_tipo],
    }