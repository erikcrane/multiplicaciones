"""Envío del PDF por correo a través de un servidor SMTP (p. ej. Brevo).

Los datos de la cuenta (usuario, contraseña, remitente y destinatarios) NO
están en este fichero: se leen de un fichero con formato `.env`, que no se
sube a git. Se usa uno solo, el primero que exista:
  1. /run/secrets/multiplicaciones_env: en Docker, el secreto
     `multiplicaciones_env` (ver docker-compose.yml).
  2. El `.env` de la carpeta del proyecto: al ejecutarlo fuera de Docker.
     Para crearlo en un ordenador nuevo, copia `.env.ejemplo` como `.env`
     y rellénalo (o copia el `.env` de otro ordenador).
Si no existe ninguno de los dos, o no se puede leer, se avisa y el programa
termina sin enviar nada.

Los datos se leen SOLO de ese fichero: las variables de entorno no se usan
ni se modifican. Así una variable que ya existiera en la terminal (de otro
proyecto, de una prueba antigua...) no puede cambiar a quién o desde dónde
se envía el correo.

El fichero solo se lee cuando se va a enviar un correo (`preparar_envio`,
al principio del programa, antes de generar el PDF, para que si falta algo
no se haga nada), así que para generar el PDF sin enviarlo no hace falta
tenerlo.

En Brevo los datos están en "SMTP & API" -> pestaña "SMTP":
  - servidor: smtp-relay.brevo.com
  - puerto: 587 con SEGURIDAD=tls (STARTTLS) o 465 con SEGURIDAD=ssl
  - usuario: el "Login" que aparece ahí (algo como 123abc@smtp-brevo.com)
  - contraseña: la "clave SMTP" que generas en esa misma página
La dirección de REMITENTE debe estar dada de alta como remitente verificado
en Brevo, o el correo será rechazado.
"""

import smtplib
import ssl
import sys
from email.message import EmailMessage
from email.utils import formataddr
from pathlib import Path

# Dónde se buscan los datos privados del correo: primero el secreto de
# Docker y, si no existe (fuera de Docker), el .env del proyecto.
RUTA_SECRETO = Path("/run/secrets/multiplicaciones_env")
RUTA_ENV_PROYECTO = Path(__file__).resolve().parent / ".env"

# Valores que se usan si el fichero no los indica.
SERVIDOR_POR_DEFECTO = "smtp-relay.brevo.com"
PUERTO_POR_DEFECTO = 465
SEGURIDAD_POR_DEFECTO = "ssl"  # "tls" (STARTTLS, puerto 587) o "ssl" (puerto 465)


def fichero_env():
    """Devuelve la ruta del fichero de datos: el secreto o el .env."""
    return RUTA_SECRETO if RUTA_SECRETO.exists() else RUTA_ENV_PROYECTO


def cargar_env(ruta):
    """Lee las líneas CLAVE=valor del fichero y las devuelve en un diccionario.

    Ignora las líneas vacías y las que empiezan por '#', y quita las
    comillas que rodeen el valor. No toca las variables de entorno. Si el
    fichero no existe o no se puede leer, termina el programa con un error.
    """
    if not ruta.exists():
        sys.exit(
            f"No se encuentra el fichero con los datos del correo: {ruta}\n"
            "Crea el .env a partir de .env.ejemplo (o, en Docker, revisa el "
            "secreto en docker-compose.yml)."
        )
    try:
        contenido = ruta.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        sys.exit(f"No se puede leer el fichero con los datos del correo {ruta}: {error}")

    datos = {}
    for linea in contenido.splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        clave, valor = linea.split("=", 1)
        valor = valor.strip()
        if len(valor) >= 2 and valor[0] == valor[-1] and valor[0] in "\"'":
            valor = valor[1:-1]
        datos[clave.strip()] = valor
    return datos


def leer_configuracion():
    """Lee el fichero de datos y devuelve la configuración del correo.

    Termina el programa con un mensaje claro si falta algún dato obligatorio
    o si alguno no es válido.
    """
    ruta = fichero_env()
    datos = cargar_env(ruta)

    texto_puerto = datos.get("PUERTO_SMTP") or str(PUERTO_POR_DEFECTO)
    try:
        puerto = int(texto_puerto)
    except ValueError:
        sys.exit(f'PUERTO_SMTP debe ser un número, no "{texto_puerto}" (en {ruta}).')

    configuracion = {
        "servidor": datos.get("SERVIDOR_SMTP") or SERVIDOR_POR_DEFECTO,
        "puerto": puerto,
        "seguridad": datos.get("SEGURIDAD") or SEGURIDAD_POR_DEFECTO,
        "usuario": datos.get("USUARIO_SMTP", ""),
        "contrasena": datos.get("CONTRASENA_SMTP", ""),
        # Dirección desde la que se envía y nombre opcional que verá el
        # destinatario.
        "remitente": datos.get("REMITENTE", ""),
        "nombre_remitente": datos.get("NOMBRE_REMITENTE", ""),
        # Direcciones a las que se envía cuando se usa -e sin indicar
        # ninguna (en el fichero, separadas por comas).
        "destinatarios": [
            direccion.strip()
            for direccion in datos.get("DESTINATARIOS", "").split(",")
            if direccion.strip()
        ],
    }
    comprobar_configuracion(configuracion, ruta)
    return configuracion


def comprobar_configuracion(configuracion, ruta):
    """Sale con un mensaje claro si falta algún dato de la configuración."""
    faltan = [
        nombre
        for nombre, clave in (
            ("USUARIO_SMTP", "usuario"),
            ("CONTRASENA_SMTP", "contrasena"),
            ("REMITENTE", "remitente"),
        )
        if not configuracion[clave]
    ]
    if faltan:
        sys.exit(
            f"Falta configurar {', '.join(faltan)}: no están en {ruta} "
            "(ver .env.ejemplo)."
        )
    if configuracion["seguridad"] not in ("tls", "ssl"):
        sys.exit(f'SEGURIDAD debe ser "tls" o "ssl", no "{configuracion["seguridad"]}".')


def crear_mensaje(configuracion, destinatarios, asunto, texto, ruta_pdf):
    """Construye el correo con el PDF adjunto."""
    ruta_pdf = Path(ruta_pdf)
    remitente = configuracion["remitente"]
    nombre = configuracion["nombre_remitente"]
    mensaje = EmailMessage()
    mensaje["From"] = formataddr((nombre, remitente)) if nombre else remitente
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


def preparar_envio(direcciones):
    """Lee la configuración del correo y decide a quién se envía.

    Se llama al principio del programa, antes de generar el PDF, para que
    si falta el fichero o algún dato se corte sin haber hecho nada. Sin
    direcciones usa los DESTINATARIOS del fichero.

    Devuelve (configuracion, destinatarios) para pasárselos a `enviar_pdf`.
    """
    configuracion = leer_configuracion()
    destinatarios = list(direcciones) or configuracion["destinatarios"]
    if not destinatarios:
        sys.exit(
            "No hay destinatarios: indícalos con -e DIRECCION o rellena "
            "DESTINATARIOS en el fichero .env."
        )
    return configuracion, destinatarios


def enviar_pdf(configuracion, destinatarios, asunto, texto, ruta_pdf):
    """Envía el PDF por SMTP con lo que ha devuelto `preparar_envio`."""
    mensaje = crear_mensaje(configuracion, destinatarios, asunto, texto, ruta_pdf)
    contexto = ssl.create_default_context()
    servidor_smtp = configuracion["servidor"]
    puerto = configuracion["puerto"]

    try:
        if configuracion["seguridad"] == "ssl":
            servidor = smtplib.SMTP_SSL(servidor_smtp, puerto, context=contexto, timeout=30)
        else:
            servidor = smtplib.SMTP(servidor_smtp, puerto, timeout=30)
        with servidor:
            if configuracion["seguridad"] == "tls":
                servidor.starttls(context=contexto)
            servidor.login(configuracion["usuario"], configuracion["contrasena"])
            servidor.send_message(mensaje)
    except smtplib.SMTPAuthenticationError:
        sys.exit("El servidor SMTP ha rechazado el usuario o la contraseña.")
    except (smtplib.SMTPException, OSError) as error:
        sys.exit(f"No se ha podido enviar el correo: {error}")

    print(f"Correo enviado a: {', '.join(destinatarios)}")
