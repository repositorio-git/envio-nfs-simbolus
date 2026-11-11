"""Diagnostico: o Firebird do Simbolus aceita conexao, e em que versao?

Existe para responder duas coisas antes de escrever dados/conexao.py: a
versao do engine (decide entre fdb e firebird-driver) e se as tabelas de
controle ja estao la (premissa da secao 7.2 do documento de requisitos).

    python testar_firebird.py

Chaves esperadas no .env (nao versionado):
    FIREBIRD_HOST=10.1.253.55
    FIREBIRD_PORT=3050
    FIREBIRD_DATABASE=C:\\caminho\\no\\servidor\\SIMBOLUS.FDB
    FIREBIRD_USUARIO=SYSDBA
    FIREBIRD_SENHA=...
"""
import os
import sys

from ambiente import carregar_env

carregar_env()

host = os.environ.get("FIREBIRD_HOST")
if not host:
    sys.exit("FIREBIRD_HOST nao definido -- preencha o .env (ver docstring)")

try:
    import fdb
except Exception as erro:
    sys.exit(f"import fdb falhou: {erro}")

print(f"conectando em {host}:{os.environ.get('FIREBIRD_PORT', '3050')}")
con = fdb.connect(
    host=host,
    port=int(os.environ.get("FIREBIRD_PORT", 3050)),
    database=os.environ.get("FIREBIRD_DATABASE", ""),
    user=os.environ.get("FIREBIRD_USUARIO", "SYSDBA"),
    password=os.environ.get("FIREBIRD_SENHA", ""),
    charset="UTF8",
)
cur = con.cursor()

cur.execute("SELECT rdb$get_context('SYSTEM', 'ENGINE_VERSION') FROM rdb$database")
print("engine:", cur.fetchone()[0])

cur.execute(
    "SELECT rdb$relation_name FROM rdb$relations "
    "WHERE rdb$relation_name IN ('NFSE_LOTE', 'NFSE_RPS')"
)
print("tabelas de controle:", [nome.strip() for (nome,) in cur.fetchall()])

con.close()
print("OK")
