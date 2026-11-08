"""Generación de los enunciados y del PDF de la hoja de multiplicaciones.

Recibe las parejas (tabla, factor) ya generadas por `multiplicaciones.py`,
las convierte en problemas con temática de perros usando los datos de
`situaciones.py` y escribe la hoja en un PDF, con una tabla de multiplicar
de referencia al final.
"""

import random
import re
import sys
import urllib.request
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from situaciones import OBJETOS, PLANTILLAS, RELACIONES

# Fuente del texto de los enunciados. Puede ser:
#   - una fuente estándar de PDF: "Helvetica", "Times-Roman" o "Courier";
#   - la ruta a un fichero .ttf, relativa a la carpeta del script,
#     por ejemplo "fonts/Fredoka-SemiBold.ttf" (Fredoka SemiBold, licencia
#     libre SIL OFL: ver fonts/OFL-Fredoka.txt).
FONTE_TEXTO = "fonts/Fredoka-SemiBold.ttf"

# Tamaño de la letra de los enunciados, en puntos. El interlineado, los
# emojis y la línea de respuesta se ajustan solos a este tamaño.
TAMANO_TEXTO = 13.5

# Espacio en blanco entre un ejercicio y el siguiente, en puntos.
SEPARACION_EJERCICIOS = 16

# Cabecera de la hoja: un título y un texto de introducción antes de los
# ejercicios. Para quitarla, deja las dos cadenas vacías ("").
TITULO_CABECERA = "¡Bienvenido a la tienda Patitas Felices!"
TEXTO_CABECERA = (
    "Tenemos una tienda de comida y accesorios para animales y necesitamos "
    "tu ayuda. Cada día llegan cajas de juguetes, pelotas y golosinas, y "
    "además cuidamos de nuestro perrito, que come, pasea y juega sin parar. "
    "Para que todo salga bien, hemos de calcular cuántas cosas tenemos, "
    "cuánto cuestan y cuánto necesitamos. ¿Nos ayudas a resolver estos "
    "problemas?"
)

# Tabla de multiplicar de referencia, al final de la hoja. "{tabla}" se
# sustituye por el número de la tabla.
TITULO_TABLA = "Tabla del {tabla}"
# Tamaño de la letra de la tabla. Con más de TAMANO_TEXTO * 2.3 la tabla a
# menudo ya no cabe en la página 2 y salta sola a una página 3.
TAMANO_TABLA = TAMANO_TEXTO * 2.2
# Alto de las cifras en proporción al tamaño de la letra (0,70 en Fredoka,
# unos 0,7 en Helvetica). Si con otra fuente los números quedan altos o bajos
# dentro de su fila, ajusta este valor: más alto los baja, más bajo los sube.
ALTURA_CIFRAS = 0.70
COLOR_FONDO_TABLA = colors.HexColor("#FFF4D6")
COLOR_BORDE_TABLA = colors.HexColor("#C8A04A")

# Los emojis se dibujan como imágenes PNG a color de Twemoji (licencia
# CC-BY 4.0), porque reportlab no sabe usar fuentes de emojis a color.
# Se descargan una sola vez a la carpeta `emojis/` y luego se leen del disco.
CARPETA_SCRIPT = Path(__file__).resolve().parent
CARPETA_EMOJIS = CARPETA_SCRIPT / "emojis"
URL_TWEMOJI = "https://cdn.jsdelivr.net/gh/jdecked/twemoji@17.0.3/assets/72x72/{}.png"
TAMANO_EMOJI = round(TAMANO_TEXTO * 1.2, 1)  # algo mayor que la letra

# Nombre del PDF cuando no se indica -o:
#   multiplicaciones_<día-mes>_<hora>_<año>_<número>.pdf
#   por ejemplo multiplicaciones_02-11_14h30_2026_001.pdf
# El número sigue al más alto que ya haya en la carpeta y no se reinicia.
PREFIJO_PDF = "multiplicaciones"
PATRON_NUMERO_PDF = re.compile(rf"^{PREFIJO_PDF}_.*_(\d+)\.pdf$")

# Agrupamos relaciones y plantillas por contexto para elegir combinaciones
# coherentes y para que todos los tipos de enunciado tengan presencia.
RELACIONES_POR_CONTEXTO = defaultdict(list)
for contexto, id_a, id_b in RELACIONES:
    RELACIONES_POR_CONTEXTO[contexto].append((id_a, id_b))

PLANTILLAS_POR_CONTEXTO = defaultdict(list)
for contexto, plantilla in PLANTILLAS:
    PLANTILLAS_POR_CONTEXTO[contexto].append(plantilla)

CONTEXTOS = list(RELACIONES_POR_CONTEXTO)


# --- Enunciados ------------------------------------------------------------


def datos_objeto(id_objeto):
    """Devuelve (singular, plural, genero, emoji) de un objeto.

    El emoji es opcional: se admite una tupla de 3 elementos (sin emoji)
    o de 4.
    """
    datos = OBJETOS[id_objeto]

    if len(datos) == 3:
        singular, plural, genero = datos
        emoji = ""
    elif len(datos) == 4:
        singular, plural, genero, emoji = datos
    else:
        raise ValueError(
            f"El objeto {id_objeto!r} debe tener 3 o 4 datos "
            f"(singular, plural, género[, emoji]); tiene {len(datos)}."
        )

    return singular, plural, genero, emoji


def validar_datos():
    """Comprueba que las relaciones apuntan a objetos y contextos válidos."""
    for id_objeto in OBJETOS:
        datos_objeto(id_objeto)

    for contexto, id_a, id_b in RELACIONES:
        if id_a not in OBJETOS:
            raise ValueError(
                f"La relación {contexto!r} usa un objeto A desconocido: {id_a!r}."
            )
        if id_b not in OBJETOS:
            raise ValueError(
                f"La relación {contexto!r} usa un objeto B desconocido: {id_b!r}."
            )
        if contexto not in PLANTILLAS_POR_CONTEXTO:
            raise ValueError(
                f"No hay ninguna plantilla para el contexto {contexto!r}."
            )


def mostrar_salida(lineas, tabla, factores, ruta_pdf):
    """Convierte cada pareja (A, B) en un enunciado y genera un PDF.

    `tabla` es la tabla de multiplicar de referencia que va al final de la
    hoja, y `factores` los números por los que se multiplica en ella.
    """
    ejercicios = []

    for numero, (a, b) in enumerate(lineas, start=1):
        contexto = random.choice(CONTEXTOS)
        id_a, id_b = random.choice(RELACIONES_POR_CONTEXTO[contexto])
        plantilla = random.choice(PLANTILLAS_POR_CONTEXTO[contexto])

        a_singular, a_plural, a_genero, a_emoji = datos_objeto(id_a)
        b_singular, b_plural, b_genero, b_emoji = datos_objeto(id_b)

        sin_emoji = {
            "a": a,
            "b": b,
            "a_singular": a_singular,
            "a_plural": a_plural,
            "b_singular": b_singular,
            "b_plural": b_plural,
            "a_cuantos": "Cuántas" if a_genero == "f" else "Cuántos",
            "b_cuantos": "Cuántas" if b_genero == "f" else "Cuántos",
        }

        # El emoji va detrás del sustantivo, en singular y en plural.
        # Si no hay emoji, se deja el sustantivo tal cual.
        con_emoji = dict(sin_emoji)
        for prefijo, emoji in (("a", a_emoji), ("b", b_emoji)):
            if emoji:
                for forma in ("singular", "plural"):
                    clave = f"{prefijo}_{forma}"
                    con_emoji[clave] = f"{sin_emoji[clave]} {emoji}"

        # Los emojis solo se ponen en la parte que explica la situación; la
        # pregunta (desde el "¿") va sin emojis para que se lea más limpia.
        inicio_pregunta = plantilla.find("¿")
        if inicio_pregunta == -1:
            inicio_pregunta = len(plantilla)
        enunciado = (
            plantilla[:inicio_pregunta].format(**con_emoji)
            + plantilla[inicio_pregunta:].format(**sin_emoji)
        )

        ejercicios.append((numero, enunciado))

    generar_pdf(ejercicios, tabla, factores, ruta_pdf)
    print(f"PDF generado: {ruta_pdf} (tabla del {tabla})")


# --- Emojis ----------------------------------------------------------------


def nombre_twemoji(emoji):
    """Nombre del fichero de Twemoji: códigos en hexadecimal unidos por '-'.

    Twemoji quita el selector de variación U+FE0F salvo en las secuencias
    unidas con ZWJ (U+200D).
    """
    codigos = [ord(caracter) for caracter in emoji]
    if 0x200D not in codigos:
        codigos = [codigo for codigo in codigos if codigo != 0xFE0F]
    return "-".join(f"{codigo:x}" for codigo in codigos)


def emojis_usados():
    """Devuelve el conjunto de emojis que aparecen en OBJETOS."""
    return {datos_objeto(id_objeto)[3] for id_objeto in OBJETOS} - {""}


def ruta_emoji(emoji):
    return CARPETA_EMOJIS / f"{nombre_twemoji(emoji)}.png"


def preparar_emojis():
    """Descarga a `emojis/` los PNG que falten. Solo usa la red la primera vez."""
    faltan = [emoji for emoji in emojis_usados() if not ruta_emoji(emoji).exists()]
    if not faltan:
        return

    CARPETA_EMOJIS.mkdir(exist_ok=True)
    for emoji in faltan:
        url = URL_TWEMOJI.format(nombre_twemoji(emoji))
        try:
            with urllib.request.urlopen(url, timeout=15) as respuesta:
                contenido = respuesta.read()
        except OSError as error:
            sys.exit(f"No se pudo descargar el emoji {emoji} desde {url}: {error}")
        ruta_emoji(emoji).write_bytes(contenido)
        print(f"Emoji descargado: {emoji} -> {ruta_emoji(emoji).name}")


def marcar_emojis(texto):
    """Sustituye cada emoji del texto por su imagen PNG a color."""
    emojis = sorted(emojis_usados(), key=len, reverse=True)
    if not emojis:
        return texto
    patron = re.compile("|".join(re.escape(emoji) for emoji in emojis))
    return patron.sub(
        lambda m: (
            f'<img src="{ruta_emoji(m.group(0))}" '
            f'width="{TAMANO_EMOJI}" height="{TAMANO_EMOJI}" '
            f'valign="{-round(TAMANO_EMOJI * 0.21, 1)}"/>'
        ),
        texto,
    )


# --- PDF -------------------------------------------------------------------


def registrar_fuente(fuente):
    """Devuelve el nombre de fuente que entiende reportlab.

    Las fuentes estándar se devuelven tal cual. Si es un fichero .ttf, se
    registra con el nombre del fichero; como la mayoría de fuentes
    decorativas no tienen negrita, se usa la misma para normal y negrita
    (así funciona la etiqueta <b> del número del ejercicio).
    """
    if not fuente.lower().endswith(".ttf"):
        return fuente

    ruta = CARPETA_SCRIPT / fuente
    if not ruta.exists():
        sys.exit(f"No se encuentra la fuente {ruta}")

    nombre = ruta.stem
    pdfmetrics.registerFont(TTFont(nombre, str(ruta)))
    pdfmetrics.registerFontFamily(
        nombre, normal=nombre, bold=nombre, italic=nombre, boldItalic=nombre
    )
    return nombre


def tabla_multiplicar_pdf(tabla, factores, fuente):
    """Devuelve el bloque del PDF con la tabla de multiplicar ya resuelta.

    Cada fila es "tabla x factor = resultado", en columnas para que los
    números queden alineados. El bloque no se parte entre dos páginas.
    """
    estilo_titulo = ParagraphStyle(
        "titulo_tabla",
        fontName=fuente,
        fontSize=TAMANO_TABLA * 1.3,
        leading=TAMANO_TABLA * 1.3 * 1.3,
        alignment=TA_CENTER,
        spaceAfter=TAMANO_TEXTO * 0.6,
    )
    titulo = Paragraph(escape(TITULO_TABLA.format(tabla=tabla)), estilo_titulo)

    filas = [
        [str(tabla), "x", str(factor), "=", str(tabla * factor)]
        for factor in factores
    ]
    ancho = TAMANO_TABLA * 1.6

    # Centrado vertical: reportlab coloca el texto de cada celda según el
    # interlineado (LEADING), que por defecto vale 12 aunque la letra sea más
    # grande, y por eso el texto bajaba hasta tocar la línea. Las cifras
    # miden ALTURA_CIFRAS de la letra de alto; con este interlineado su centro
    # queda justo en el centro de la fila (el texto se apoya en la línea base
    # y reportlab la pone en centro + interlineado/2 - tamaño).
    interlineado = TAMANO_TABLA * (2 - ALTURA_CIFRAS)

    cuadro = Table(
        filas,
        colWidths=[ancho, ancho * 0.8, ancho, ancho * 0.8, ancho * 1.3],
        rowHeights=TAMANO_TABLA * 1.6,
    )
    cuadro.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), fuente),
                ("FONTSIZE", (0, 0), (-1, -1), TAMANO_TABLA),
                ("LEADING", (0, 0), (-1, -1), interlineado),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("ALIGN", (-1, 0), (-1, -1), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("RIGHTPADDING", (-1, 0), (-1, -1), TAMANO_TABLA * 0.8),
                ("BACKGROUND", (0, 0), (-1, -1), COLOR_FONDO_TABLA),
                ("BOX", (0, 0), (-1, -1), 1.5, COLOR_BORDE_TABLA),
                ("LINEBELOW", (0, 0), (-1, -2), 0.5, COLOR_BORDE_TABLA),
            ]
        )
    )

    return KeepTogether([titulo, cuadro])


def generar_pdf(ejercicios, tabla, factores, ruta_pdf):
    """Escribe los enunciados y la tabla de referencia en un documento PDF."""
    fuente = registrar_fuente(FONTE_TEXTO)
    estilo_titulo = ParagraphStyle(
        "titulo",
        fontName=fuente,
        fontSize=TAMANO_TEXTO * 1.6,
        leading=TAMANO_TEXTO * 1.6 * 1.3,
        alignment=TA_CENTER,
        spaceAfter=TAMANO_TEXTO,
    )
    estilo_introduccion = ParagraphStyle(
        "introduccion",
        fontName=fuente,
        fontSize=TAMANO_TEXTO,
        leading=TAMANO_TEXTO * 1.4,
        alignment=TA_JUSTIFY,
        spaceAfter=SEPARACION_EJERCICIOS * 1.5,
    )
    estilo_enunciado = ParagraphStyle(
        "enunciado",
        fontName=fuente,
        fontSize=TAMANO_TEXTO,
        leading=TAMANO_TEXTO * 1.4,
    )
    estilo_respuesta = ParagraphStyle(
        "respuesta",
        fontName="Courier-Bold",
        fontSize=TAMANO_TEXTO,
        leading=TAMANO_TEXTO * 1.4,
        leftIndent=14,
        spaceAfter=SEPARACION_EJERCICIOS,
    )

    documento = SimpleDocTemplate(
        str(ruta_pdf),
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title="Generador de multiplicaciones",
        author="multiplicaciones.py",
    )

    historia = []
    if TITULO_CABECERA:
        historia.append(Paragraph(escape(TITULO_CABECERA), estilo_titulo))
    if TEXTO_CABECERA:
        historia.append(Paragraph(escape(TEXTO_CABECERA), estilo_introduccion))

    for numero, enunciado in ejercicios:
        texto = marcar_emojis(escape(enunciado))
        historia.append(Paragraph(f"<b>{numero}.</b> {texto}", estilo_enunciado))
        historia.append(Spacer(1, TAMANO_TEXTO * 0.7))
        historia.append(Paragraph("____ x ____ = ____", estilo_respuesta))

    historia.append(Spacer(1, SEPARACION_EJERCICIOS))
    historia.append(tabla_multiplicar_pdf(tabla, factores, fuente))

    documento.build(historia)


def nombre_pdf_automatico(carpeta=Path(".")):
    """Devuelve la ruta del siguiente PDF numerado dentro de `carpeta`."""
    numeros = [
        int(coincidencia.group(1))
        for fichero in carpeta.glob(f"{PREFIJO_PDF}_*.pdf")
        if (coincidencia := PATRON_NUMERO_PDF.match(fichero.name))
    ]
    siguiente = max(numeros, default=0) + 1
    ahora = datetime.now()
    nombre = f"{PREFIJO_PDF}_{ahora:%d-%m}_{ahora:%Hh%M}_{ahora:%Y}_{siguiente:03d}.pdf"
    return carpeta / nombre
