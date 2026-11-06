"""
Módulo de Envio de E-mails do Klynner Suite.
Gerencia conexões SMTP seguras (TLS/SSL) e renderiza e-mails transacionais
para respostas oficiais a comentários e sugestões de usuários.
"""

from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr, parseaddr
import html
import logging
import os
from pathlib import Path
import smtplib
from typing import Any, Dict, Optional

logger = logging.getLogger("email_service")


def get_smtp_config() -> Dict[str, Any]:
    """Lê e retorna as configurações de SMTP a partir das variáveis de ambiente."""
    return {
        "host": os.environ.get("SMTP_HOST", "").strip(),
        "port": int(os.environ.get("SMTP_PORT", "587")),
        "user": os.environ.get("SMTP_USER", "").strip(),
        "password": os.environ.get("SMTP_PASSWORD", os.environ.get("SMTP_PASS", "")).strip(),
        "sender": os.environ.get("SMTP_FROM", os.environ.get("EMAIL_FROM", "Klynner Suite <contato@klynner.com.br>")).strip(),
        "use_tls": os.environ.get("SMTP_USE_TLS", "true").lower() in ("true", "1", "yes"),
        "use_ssl": os.environ.get("SMTP_USE_SSL", "false").lower() in ("true", "1", "yes"),
        "timeout": float(os.environ.get("SMTP_TIMEOUT", "15.0")),
    }


def is_smtp_configured() -> bool:
    """Verifica se os parâmetros mínimos de host e autenticação SMTP estão preenchidos."""
    cfg = get_smtp_config()
    return bool(cfg["host"])


def render_reply_email_html(
    recipient_name: str,
    original_message: str,
    reply_message: str,
    replied_by: str = "Equipe Klynner"
) -> str:
    """Gera o corpo HTML do e-mail com design moderno e visual escuro/profissional."""
    clean_name = html.escape(recipient_name or "Usuário")
    clean_orig = html.escape(original_message).replace("\n", "<br>")
    clean_reply = html.escape(reply_message).replace("\n", "<br>")
    clean_author = html.escape(replied_by or "Equipe Klynner")

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Resposta ao seu comentário no Klynner Suite</title>
  <style>
    body {{
      margin: 0;
      padding: 0;
      background-color: #0b0f19;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
      color: #e2e8f0;
      -webkit-font-smoothing: antialiased;
    }}
    .email-wrapper {{
      width: 100%;
      background-color: #0b0f19;
      padding: 32px 16px;
    }}
    .email-container {{
      max-width: 600px;
      margin: 0 auto;
      background: #131b2e;
      border: 1px solid #1e293b;
      border-radius: 16px;
      overflow: hidden;
      box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.5);
    }}
    .email-header {{
      background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
      padding: 28px 32px;
      border-bottom: 1px solid #1e293b;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }}
    .brand-title {{
      font-size: 20px;
      font-weight: 700;
      color: #ffffff;
      letter-spacing: -0.5px;
      margin: 0;
    }}
    .brand-badge {{
      display: inline-block;
      background: rgba(59, 130, 246, 0.15);
      border: 1px solid rgba(59, 130, 246, 0.35);
      color: #60a5fa;
      font-size: 11px;
      font-weight: 600;
      padding: 4px 10px;
      border-radius: 9999px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }}
    .email-body {{
      padding: 32px;
    }}
    .greeting {{
      font-size: 18px;
      font-weight: 600;
      color: #f8fafc;
      margin: 0 0 16px 0;
    }}
    .intro-text {{
      font-size: 15px;
      line-height: 1.6;
      color: #94a3b8;
      margin: 0 0 24px 0;
    }}
    .box-original {{
      background: rgba(15, 23, 42, 0.6);
      border-left: 3px solid #64748b;
      border-radius: 0 8px 8px 0;
      padding: 14px 18px;
      margin: 0 0 24px 0;
    }}
    .box-original-label {{
      font-size: 12px;
      font-weight: 600;
      color: #94a3b8;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      margin-bottom: 6px;
    }}
    .box-original-text {{
      font-size: 14px;
      line-height: 1.5;
      color: #cbd5e1;
      font-style: italic;
      margin: 0;
    }}
    .box-reply {{
      background: linear-gradient(180deg, rgba(30, 58, 138, 0.15) 0%, rgba(15, 23, 42, 0.6) 100%);
      border: 1px solid rgba(59, 130, 246, 0.3);
      border-radius: 12px;
      padding: 20px;
      margin: 0 0 28px 0;
    }}
    .box-reply-header {{
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 12px;
    }}
    .box-reply-author {{
      font-size: 14px;
      font-weight: 700;
      color: #38bdf8;
    }}
    .box-reply-tag {{
      background: #10b981;
      color: #ffffff;
      font-size: 10px;
      font-weight: 700;
      padding: 2px 6px;
      border-radius: 4px;
      text-transform: uppercase;
    }}
    .box-reply-text {{
      font-size: 15px;
      line-height: 1.6;
      color: #f1f5f9;
      margin: 0;
    }}
    .cta-container {{
      text-align: center;
      margin: 32px 0 16px 0;
    }}
    .cta-button {{
      display: inline-block;
      background: #2563eb;
      color: #ffffff !important;
      font-size: 15px;
      font-weight: 600;
      text-decoration: none;
      padding: 12px 28px;
      border-radius: 8px;
      box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
    }}
    .email-footer {{
      background: #0f172a;
      padding: 20px 32px;
      border-top: 1px solid #1e293b;
      text-align: center;
      font-size: 12px;
      color: #64748b;
      line-height: 1.5;
    }}
    .email-footer a {{
      color: #38bdf8;
      text-decoration: none;
    }}
  </style>
</head>
<body>
  <div class="email-wrapper">
    <div class="email-container">
      <div class="email-header">
        <h1 class="brand-title">Klynner Suite</h1>
        <span class="brand-badge">Resposta Oficial</span>
      </div>
      <div class="email-body">
        <h2 class="greeting">Olá, {clean_name}!</h2>
        <p class="intro-text">
          Agradecemos imensamente por compartilhar sua experiência e sugestão na nossa plataforma.
          Nossa equipe analisou seu comentário e preparou a seguinte resposta oficial:
        </p>

        <div class="box-original">
          <div class="box-original-label">Sua mensagem:</div>
          <p class="box-original-text">"{clean_orig}"</p>
        </div>

        <div class="box-reply">
          <div class="box-reply-header">
            <span class="box-reply-author">{clean_author}</span>
            <span class="box-reply-tag">Resposta Oficial</span>
          </div>
          <p class="box-reply-text">{clean_reply}</p>
        </div>

        <p class="intro-text" style="margin-bottom: 0;">
          Suas sugestões são fundamentais para continuarmos evoluindo o Klynner como a melhor suíte de produtividade em documentos.
        </p>

        <div class="cta-container">
          <a href="https://klynner.com.br" class="cta-button" target="_blank">Acessar o Klynner Suite</a>
        </div>
      </div>
      <div class="email-footer">
        <p style="margin: 0 0 6px 0;">
          Você recebeu este e-mail porque enviou uma mensagem através do Mural da Comunidade em <a href="https://klynner.com.br">klynner.com.br</a>.
        </p>
        <p style="margin: 0;">
          Klynner Suite &bull; Processamento Seguro e Privativo de Documentos
        </p>
      </div>
    </div>
  </div>
</body>
</html>"""


def render_reply_email_plain(
    recipient_name: str,
    original_message: str,
    reply_message: str,
    replied_by: str = "Equipe Klynner"
) -> str:
    """Gera versão em texto puro para clientes de e-mail sem suporte a HTML."""
    name = recipient_name or "Usuário"
    author = replied_by or "Equipe Klynner"

    return f"""Olá, {name}!

Agradecemos imensamente por compartilhar sua experiência e sugestão no Klynner Suite.

Sua mensagem original:
"{original_message}"

--------------------------------------------------
Resposta Oficial ({author}):
{reply_message}
--------------------------------------------------

Suas sugestões são fundamentais para continuarmos evoluindo a plataforma.

Acesse o Klynner Suite: https://klynner.com.br

---
Klynner Suite - Processamento Seguro e Privativo de Documentos
Você recebeu esta mensagem porque enviou um feedback no site klynner.com.br.
"""


def send_feedback_reply_email(
    to_email: str,
    recipient_name: Optional[str],
    original_message: str,
    reply_message: str,
    replied_by: str = "Equipe Klynner",
    subject: Optional[str] = None
) -> Dict[str, Any]:
    """
    Envia a resposta oficial por e-mail para o usuário usando SMTP autenticado.
    Caso o SMTP não esteja configurado, opera em modo simulado/mock seguro.
    """
    if not to_email or "@" not in to_email:
        return {
            "success": False,
            "delivered": False,
            "error": "Endereço de e-mail do destinatário ausente ou inválido.",
            "recipient": to_email,
        }

    cfg = get_smtp_config()
    clean_subject = (subject or "").strip() or "Sua mensagem no Klynner Suite foi respondida!"

    # Se SMTP não estiver configurado no servidor, registra aviso e retorna status claro
    if not cfg["host"]:
        logger.warning(
            f"SMTP não configurado no ambiente. E-mail simulado com sucesso: para={to_email}, "
            f"assunto='{clean_subject}'."
        )
        return {
            "success": True,
            "delivered": False,
            "mock": True,
            "recipient": to_email,
            "message": "SMTP não configurado no servidor. A resposta foi salva no mural, mas o e-mail não pôde ser disparado fisicamente.",
        }

    recipient_name_clean = (recipient_name or "").strip() or "Usuário"
    html_body = render_reply_email_html(recipient_name_clean, original_message, reply_message, replied_by)
    plain_body = render_reply_email_plain(recipient_name_clean, original_message, reply_message, replied_by)

    # Monta mensagem MIME multipart/alternative
    msg = MIMEMultipart("alternative")
    msg["Subject"] = str(Header(clean_subject, "utf-8"))
    msg["To"] = formataddr((recipient_name_clean, to_email))

    # Formata remetente
    sender_name, sender_addr = parseaddr(cfg["sender"])
    if not sender_addr:
        sender_addr = cfg["user"] or "contato@klynner.com.br"
        sender_name = "Klynner Suite"
    msg["From"] = formataddr((str(Header(sender_name, "utf-8")), sender_addr))

    # Anexa partes texto e HTML
    msg.attach(MIMEText(plain_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        if cfg["use_ssl"]:
            server = smtplib.SMTP_SSL(cfg["host"], cfg["port"], timeout=cfg["timeout"])
        else:
            server = smtplib.SMTP(cfg["host"], cfg["port"], timeout=cfg["timeout"])
            if cfg["use_tls"]:
                server.starttls()

        if cfg["user"] and cfg["password"]:
            server.login(cfg["user"], cfg["password"])

        server.send_message(msg)
        server.quit()

        logger.info(f"E-mail de resposta enviado com sucesso para {to_email} via SMTP ({cfg['host']}:{cfg['port']}).")
        return {
            "success": True,
            "delivered": True,
            "mock": False,
            "recipient": to_email,
            "message": f"E-mail enviado com sucesso para {to_email}.",
        }

    except smtplib.SMTPAuthenticationError as auth_err:
        err_msg = f"Falha de autenticação SMTP: {auth_err.smtp_error.decode('utf-8', errors='ignore') if hasattr(auth_err, 'smtp_error') else str(auth_err)}"
        logger.error(err_msg)
        return {
            "success": False,
            "delivered": False,
            "error": err_msg,
            "recipient": to_email,
        }
    except Exception as e:
        err_msg = f"Erro ao enviar e-mail via SMTP ({cfg['host']}:{cfg['port']}): {str(e)}"
        logger.error(err_msg, exc_info=True)
        return {
            "success": False,
            "delivered": False,
            "error": err_msg,
            "recipient": to_email,
        }
