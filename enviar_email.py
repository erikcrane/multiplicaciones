"""Envío del PDF por correo a través de un servidor SMTP (p. ej. Brevo).

Los datos de la cuenta (usuario, contraseña, remitente y destinatarios) NO
están en este fichero: se leen del fichero `.env` de la carpeta del
proyecto, que no se sube a git. Para crearlo en un ordenador nuevo, copia
`.env.ejemplo` como `.env` y rellénalo (o copia el `.env` de otro ordenador).
Si una variable ya existe en el entorno (por ejemplo en Docker, con
`env_file` en docker-compose.yml), tiene prioridad sobre el `.env`.

En Brevo los datos están en "SMTP & API" -> pestaña "SMTP":
  - servidor: smtp-relay.brevo.com
  - puerto: 587 con SEGURIDAD=tls (STARTTLS) o 465 con SEGURIDAD=ssl
  - usuario: el "Login" que aparece ahí (algo como 123abc@smtp-brevo.com)
  - contraseña: la "clave SMTP" que generas en esa misma página
La dirección de REMITENTE debe estar dada de alta como remitente verificado
en Brevo, o el correo será rechazado.
"""

import os
import smtplib
import ssl
import sys
from email.message import EmailMessage
from email.utils import formataddr
from pathlib import Path

FICHERO_ENV = Path(__file__).resolve().parent / ".env"


def cargar_env(ruta=FICHERO_ENV):
    """Lee las líneas CLAVE=valor del fichero `.env` y las pone en el entorno.

    Ignora las líneas vacías y las que empiezan por '#'. No pisa variables
    que ya existan en el entorno. Si el fichero no existe, no hace nada.
    """
    if not ruta.exists():
        return
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        clave, valor = linea.split("=", 1)
        valor = valor.strip()
        if len(valor) >= 2 and valor[0] == valor[-1] and valor[0] in "\"'":
            valor = valor[1:-1]
        os.environ.setdefault(clave.strip(), valor)


cargar_env()

# ---------------------------------------------------------------------------
# Configuración del servidor SMTP (se rellena desde el .env)
# ---------------------------------------------------------------------------
SERVIDOR_SMTP = os.environ.get("SERVIDOR_SMTP", "smtp-relay.brevo.com")
PUERTO_SMTP = int(os.environ.get("PUERTO_SMTP") or 465)
USUARIO_SMTP = os.environ.get("USUARIO_SMTP", "")
CONTRASENA_SMTP = os.environ.get("CONTRASENA_SMTP", "")
SEGURIDAD = os.environ.get("SEGURIDAD", "ssl")  # "tls" (STARTTLS, puerto 587) o "ssl" (puerto 465)

# Dirección desde la que se envía (y nombre opcional que verá el destinatario).
REMITENTE = os.environ.get("REMITENTE", "")
NOMBRE_REMITENTE = os.environ.get("NOMBRE_REMITENTE", "")

# Direcciones a las que se envía cuando se usa -e sin indicar ninguna
# (en el .env, separadas por comas).
DESTINATARIOS = [
    direccion.strip()
    for direccion in os.environ.get("DESTINATARIOS", "").split(",")
    if direccion.strip()
]
# ---------------------------------------------------------------------------


def crear_mensaje(destinatarios, asunto, texto, ruta_pdf):
    """Construye el correo con el PDF adjunto."""
    ruta_pdf = Path(ruta_pdf)
    mensaje = EmailMessage()
    mensaje["From"] = formataddr((NOMBRE_REMITENTE, REMITENTE)) if NOMBRE_REMITENTE else REMITENTE
    mensaje["To"] = ", ".join(destinatarios)
    mensaje["Subject"] = asunto
    mensaje.set_content(texto)
    mensaje.add_attachment(
        ruta_pdf.read_bytes(),
        maintype="application",
        subtype="pdf",
        filename=ruta_pdf.name,
    )
    return mensaje


def comprobar_configuracion():
    """Sale con un mensaje claro si falta algún dato de la configuración."""
    faltan = [
        nombre
        for nombre, valor in (
            ("SERVIDOR_SMTP", SERVIDOR_SMTP),
            ("PUERTO_SMTP", PUERTO_SMTP),
            ("USUARIO_SMTP", USUARIO_SMTP),
            ("CONTRASENA_SMTP", CONTRASENA_SMTP),
            ("REMITENTE", REMITENTE),
        )
        if not valor
    ]
    if faltan:
        sys.exit(
            f"Falta configurar {', '.join(faltan)} en el fichero .env (ver .env.ejemplo)."
        )
    if SEGURIDAD not in ("tls", "ssl"):
        sys.exit(f'SEGURIDAD debe ser "tls" o "ssl", no "{SEGURIDAD}".')


def enviar_pdf(destinatarios, asunto, texto, ruta_pdf):
    """Envía el PDF por SMTP. Sin destinatarios usa los de DESTINATARIOS."""
    comprobar_configuracion()
    destinatarios = list(destinatarios) or list(DESTINATARIOS)
    if not destinatarios:
        sys.exit(
            "No hay destinatarios: indícalos con -e DIRECCION o rellena "
            "DESTINATARIOS en el fichero .env."
        )

    mensaje = crear_mensaje(destinatarios, asunto, texto, ruta_pdf)
    contexto = ssl.create_default_context()

    try:
        if SEGURIDAD == "ssl":
            servidor = smtplib.SMTP_SSL(SERVIDOR_SMTP, PUERTO_SMTP, context=contexto, timeout=30)
        else:
            servidor = smtplib.SMTP(SERVIDOR_SMTP, PUERTO_SMTP, timeout=30)
        with servidor:
            if SEGURIDAD == "tls":
                servidor.starttls(context=contexto)
            servidor.login(USUARIO_SMTP, CONTRASENA_SMTP)
            servidor.send_message(mensaje)
    except smtplib.SMTPAuthenticationError:
        sys.exit("El servidor SMTP ha rechazado el usuario o la contraseña.")
    except (smtplib.SMTPException, OSError) as error:
        sys.exit(f"No se ha podido enviar el correo: {error}")

    print(f"Correo enviado a: {', '.join(destinatarios)}")
