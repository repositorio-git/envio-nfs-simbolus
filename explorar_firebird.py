"""Diagnostico: explora o schema do Firebird do Simbolus pra achar a(s)
tabela(s) de Contas a Receber -- onde ficam as notas elegiveis por tipo
de conta (Manutencao/Sepultamento/Lapide/Jazigos). Sao tabelas DIFERENTES
de NFSE_LOTE/NFSE_RPS (essas sao de controle, criadas pelo proprio robo).
Existe pra fundamentar RF-14a (contagem de elegiveis pra timeout
dinamico) e o loop principal da Fase 1.

Uso:
    python explorar_firebird.py                  # lista todas as tabelas de usuario
    python explorar_firebird.py TITULO           # so tabelas com "TITULO" no nome
    python explorar_firebird.py --colunas NOME_DA_TABELA
"""
import os
import sys

from ambiente import carregar_env

carregar_env()

try:
    import fdb
except Exception as erro:
    sys.exit(f"import fdb falhou: {erro}")

con = fdb.connect(
    host=os.environ["FIREBIRD_HOST"],
    port=int(os.environ.get("FIREBIRD_PORT", 3050)),
    database=os.environ["FIREBIRD_DATABASE"],
    user=os.environ.get("FIREBIRD_USUARIO", "SYSDBA"),
    password=os.environ.get("FIREBIRD_SENHA", ""),
    charset="UTF8",
)
cur = con.cursor()

argv = sys.argv[1:]

if argv and argv[0] == "--colunas":
    if len(argv) < 2:
        sys.exit("uso: python explorar_firebird.py --colunas NOME_DA_TABELA")
    cur.execute(
        "SELECT rf.rdb$field_name, f.rdb$field_type, f.rdb$field_length "
        "FROM rdb$relation_fields rf "
        "JOIN rdb$fields f ON f.rdb$field_name = rf.rdb$field_source "
        "WHERE rf.rdb$relation_name = ? "
        "ORDER BY rf.rdb$field_position",
        (argv[1].upper(),),
    )
    linhas = cur.fetchall()
    if not linhas:
        print(f"'{argv[1]}' nao encontrada (nome tem que bater exato, sem acento)")
    for nome, tipo, tamanho in linhas:
        print(f"{nome.strip():<32} tipo={tipo} tamanho={tamanho}")
else:
    sql = "SELECT rdb$relation_name FROM rdb$relations WHERE rdb$system_flag = 0"
    parametros = ()
    if argv:
        sql += " AND rdb$relation_name LIKE ?"
        parametros = (f"%{argv[0].upper()}%",)
    cur.execute(sql + " ORDER BY rdb$relation_name", parametros)
    for (nome,) in cur.fetchall():
        print(nome.strip())

con.close()
