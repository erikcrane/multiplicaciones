#!/usr/bin/env python3
"""Generador de multiplicaciones con temática de perros.

Reglas:
  - Nunca se usan el 0, el 1 ni el 10, ni en las tablas ni en los factores.
  - Las tablas y los factores válidos van del 2 al 9.
  - Sin argumentos se usan las tablas predefinidas (2..9).
  - Con argumentos, esos números son las únicas tablas que aparecen.
  - Los argumentos repetidos se ignoran.
  - Al final de la hoja va una tabla de multiplicar de referencia, ya
    resuelta, elegida al azar. No se repite ninguna tabla hasta que han
    salido todas (ver `elegir_tabla`).

Este módulo solo genera las multiplicaciones "en bruto". Los enunciados y
el PDF se generan en `generacion_pdf.py`, mediante `mostrar_salida`, para
poder cambiar más adelante el destino sin tocar el resto del programa.
"""

import argparse
import json
import random
from pathlib import Path

from enviar_email import enviar_pdf
from generacion_pdf import (
    mostrar_salida,
    nombre_pdf_automatico,
    preparar_emojis,
    validar_datos,
)

# Correo que se envía con la opción --email (el PDF va adjunto).
ASUNTO_EMAIL = "Ficha de multiplicaciones"
TEXTO_EMAIL = (
    "¡Hola!\n\n"
    "Te envío una nueva ficha de multiplicaciones de la tienda Patitas Felices.\n\n"
    "¡Mucho ánimo!"
)

NUM_EJERCICIOS = 10

# Números que pueden aparecer en una multiplicación (se excluyen 0, 1 y 10).
# Se usan tanto para las tablas (el primer número) como para el número por
# el que se multiplica (el segundo). Sin argumentos se usan todas las tablas.
NUMEROS_VALIDOS = (2, 3, 4, 5, 6, 7, 8, 9)

# Fichero donde se guardan las tablas de referencia que ya han salido en la
# ronda actual. Se crea en la carpeta desde la que se ejecuta (la misma de
# los PDF). Una tabla no se repite hasta que han salido todas las demás.
FICHERO_TABLAS_SALIDAS = Path("tablas_salidas.json")


def fix_adjacent_dups(items):
    """Evita, cuando puede, que haya elementos iguales consecutivos."""
    for i in range(1, len(items)):
        if items[i] == items[i - 1]:
            for j in range(i + 1, len(items)):
                if items[j] != items[i]:
                    items[i], items[j] = items[j], items[i]
                    break


def generar_lineas(tablas, num_ejercicios):
    """Genera las parejas (tabla, factor) que se convertirán en enunciados."""
    combinaciones = [(tabla, factor) for tabla in tablas for factor in NUMEROS_VALIDOS]
    total = len(combinaciones)

    if total >= num_ejercicios:
        random.shuffle(combinaciones)
        lineas = combinaciones[:num_ejercicios]
    else:
        # Todas las combinaciones tantas veces como quepan enteras, y el
        # resto se completa con combinaciones al azar.
        reps, rem = divmod(num_ejercicios, total)
        pool = combinaciones * reps
        random.shuffle(combinaciones)
        pool.extend(combinaciones[:rem])
        random.shuffle(pool)
        lineas = pool

    fix_adjacent_dups(lineas)

    return lineas


def leer_tablas_salidas():
    """Devuelve la lista de tablas de referencia que ya han salido en la ronda.

    Si el fichero no existe o está estropeado, se empieza una ronda nueva.
    """
    try:
        datos = json.loads(FICHERO_TABLAS_SALIDAS.read_text())
    except (OSError, ValueError):
        return []
    if not isinstance(datos, list):
        return []
    return [tabla for tabla in datos if tabla in NUMEROS_VALIDOS]


def guardar_tablas_salidas(salidas):
    FICHERO_TABLAS_SALIDAS.write_text(json.dumps(salidas))


def elegir_tabla():
    """Elige al azar la tabla de referencia de la hoja.

    Solo se elige entre las que aún no han salido en la ronda. Cuando ya han
    salido todas, empieza una ronda nueva, pero sin repetir la última que
    salió (así nunca hay dos hojas seguidas con la misma tabla).

    Devuelve (tabla, salidas): `salidas` es la lista que hay que guardar con
    `guardar_tablas_salidas` una vez generado el PDF.
    """
    salidas = leer_tablas_salidas()
    pendientes = [tabla for tabla in NUMEROS_VALIDOS if tabla not in salidas]

    if not pendientes:
        ultima = salidas[-1]
        pendientes = [tabla for tabla in NUMEROS_VALIDOS if tabla != ultima]
        salidas = []

    tabla = random.choice(pendientes)
    return tabla, salidas + [tabla]


def parsear_tablas(valores, parser):
    tablas = []

    for valor in valores:
        try:
            tabla = int(valor)
        except ValueError:
            parser.error(f"'{valor}' no es un número entero válido.")

        if tabla not in NUMEROS_VALIDOS:
            parser.error(
                f"la tabla '{tabla}' no está permitida. "
                "Solo se admiten tablas del 2 al 9 (se excluyen 0, 1 y 10)."
            )

        if tabla not in tablas:
            tablas.append(tabla)

    return tablas or list(NUMEROS_VALIDOS)


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="multiplicaciones.py",
        description="Genera multiplicaciones con enunciados de temática perruna.",
        epilog=(
            "Ejemplos:\n"
            "  python3 multiplicaciones.py\n"
            "  python3 multiplicaciones.py 3 6 9\n"
            "  python3 multiplicaciones.py 3 6 9 -o tablas.pdf\n"
            "  python3 multiplicaciones.py --email alguien@gmail.com\n"
            "  python3 multiplicaciones.py 3 6 9 -e"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "tablas",
        nargs="*",
        metavar="tabla",
        help="tablas del 2 al 9 (si no se indica ninguna, se usan todas)",
    )
    parser.add_argument(
        "-o",
        "--salida",
        metavar="PDF",
        help=(
            "ruta del PDF de salida (por defecto: "
            "multiplicaciones_<día-mes>_<hora>_<año>_<número>.pdf)"
        ),
    )
    parser.add_argument(
        "-e",
        "--email",
        action="append",
        nargs="?",
        const="",
        metavar="DIRECCION",
        help=(
            "envía el PDF por correo a esta dirección (se puede repetir); "
            "sin dirección, a los DESTINATARIOS de enviar_email.py"
        ),
    )
    args = parser.parse_args(argv)

    direcciones = [d for d in args.email or [] if d]
    for direccion in direcciones:
        if "@" not in direccion:
            parser.error(
                f"'{direccion}' no parece una dirección de correo "
                "(si usas -e sin dirección, ponlo después de las tablas)."
            )

    tablas = parsear_tablas(args.tablas, parser)

    try:
        validar_datos()
    except ValueError as error:
        parser.error(str(error))

    preparar_emojis()

    lineas = generar_lineas(tablas, NUM_EJERCICIOS)
    tabla, salidas = elegir_tabla()
    ruta_pdf = args.salida or nombre_pdf_automatico()
    mostrar_salida(lineas, tabla, NUMEROS_VALIDOS, ruta_pdf)
    guardar_tablas_salidas(salidas)

    if args.email is not None:
        enviar_pdf(direcciones, ASUNTO_EMAIL, TEXTO_EMAIL, ruta_pdf)


if __name__ == "__main__":
    main()
