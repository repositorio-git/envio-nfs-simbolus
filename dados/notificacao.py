"""A MEMORIA: envio de e-mail via SMTP. Mesma regra do Firebird -- host,
porta e remetente (nao-secreto) vem de configuracoes.py; a senha vem do
.env (EMAIL_SENHA).
"""
import json
import logging
import os
import smtplib
from datetime import date
from email.message import EmailMessage

logger = logging.getLogger(__name__)


class Notificador:
    def __init__(self, config: dict):
        self.host = config["email"]["smtp_host"]
        self.porta = config["email"]["smtp_port"]
        self.remetente = config["email"]["remetente"]
        self.senha = os.environ.get("EMAIL_SENHA")
        if not self.senha:
            logger.warning("EMAIL_SENHA nao definida no ambiente/.env")
        self.caminho_estado = os.path.join(config["caminhos"]["logs"], "notificacoes_enviadas.json")

    def enviar(self, destinatarios: list, assunto: str, corpo: str) -> None:
        msg = EmailMessage()
        msg["Subject"] = assunto
        msg["From"] = self.remetente
        msg["To"] = ", ".join(destinatarios)
        msg.set_content(corpo, subtype="html")

        with smtplib.SMTP(self.host, self.porta) as servidor:
            servidor.starttls()
            servidor.login(self.remetente, self.senha)
            servidor.send_message(msg)

    def _ler_estado(self) -> dict:
        if not os.path.exists(self.caminho_estado):
            return {}
        with open(self.caminho_estado, encoding="utf-8") as f:
            return json.load(f)

    def ja_enviado_hoje(self, chave: str) -> bool:
        """'chave' identifica o TIPO de relatorio (ex: 'gerados',
        'pendentes', 'pos_processamento'), nao o assunto (que varia com a
        data) -- e o que permite rodar o robo varias vezes no mesmo dia
        (reinicializacoes, Task Scheduler) sem reenviar o mesmo
        relatorio."""
        return self._ler_estado().get(chave) == date.today().isoformat()

    def marcar_enviado_hoje(self, chave: str) -> None:
        estado = self._ler_estado()
        estado[chave] = date.today().isoformat()
        os.makedirs(os.path.dirname(self.caminho_estado), exist_ok=True)
        with open(self.caminho_estado, "w", encoding="utf-8") as f:
            json.dump(estado, f)
