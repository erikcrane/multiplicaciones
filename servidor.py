#!/usr/bin/env python3
"""Servidor web mínimo para generar la hoja de multiplicaciones desde el navegador.

Sirve `index.html` y, al pulsar el botón "Generar", ejecuta
`multiplicaciones.py -e` (genera el PDF y lo envía a los DESTINATARIOS
por defecto de `enviar_email.py`).

Uso:
    env/bin/python servidor.py            # escucha en el puerto 8000
    env/bin/python servidor.py -p 8080    # otro puerto
"""

import argparse
import json
import os
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

CARPETA = Path(__file__).resolve().parent
PAGINA = CARPETA / "index.html"
SCRIPT = CARPETA / "multiplicaciones.py"

# Carpeta donde se guardan los PDF generados. Por defecto la del proyecto;
# en Docker se cambia con la variable de entorno CARPETA_PDFS (un volumen).
CARPETA_PDFS = Path(os.environ.get("CARPETA_PDFS", CARPETA))

# Segundos que hay que esperar, después de generar una hoja, antes de poder
# generar (y enviar por email) otra. Evita mandar muchos emails por error.
ESPERA_SEGUNDOS = 20

# Evita que dos pulsaciones seguidas lancen el script a la vez.
cerrojo = threading.Lock()

# Momento (reloj monotónico) en que terminó la última generación.
ultima_generacion = None


def segundos_restantes():
    """Segundos que faltan para poder generar otra hoja (0 si ya se puede)."""
    if ultima_generacion is None:
        return 0
    return max(0, ESPERA_SEGUNDOS - (time.monotonic() - ultima_generacion))


class Manejador(BaseHTTPRequestHandler):
    def _responder(self, codigo, tipo, cuerpo):
        self.send_response(codigo)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)

    def _responder_json(self, codigo, mensaje):
        # "espera": segundos que faltan para poder volver a generar; la página
        # lo usa para la cuenta atrás del botón.
        datos = {"mensaje": mensaje, "espera": round(segundos_restantes())}
        cuerpo = json.dumps(datos, ensure_ascii=False).encode()
        self._responder(codigo, "application/json; charset=utf-8", cuerpo)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self._responder(200, "text/html; charset=utf-8", PAGINA.read_bytes())
        else:
            self._responder(404, "text/plain; charset=utf-8", b"No encontrado")

    def do_POST(self):
        global ultima_generacion
        if self.path != "/generar":
            self._responder(404, "text/plain; charset=utf-8", b"No encontrado")
            return
        if not cerrojo.acquire(blocking=False):
            self._responder_json(409, "Ya se está generando una hoja, espera un momento.")
            return
        if segundos_restantes() > 0:
            cerrojo.release()
            self._responder_json(429, "Espera un poco antes de generar otra hoja.")
            return
        try:
            resultado = subprocess.run(
                [sys.executable, str(SCRIPT), "-e"],
                cwd=CARPETA_PDFS,
                capture_output=True,
                text=True,
                timeout=120,
            )
        except subprocess.TimeoutExpired:
            self._responder_json(500, "El script tardó demasiado y se ha cancelado.")
            return
        finally:
            # La espera cuenta desde que termina, haya ido bien o no.
            ultima_generacion = time.monotonic()
            cerrojo.release()

        if resultado.returncode == 0:
            print(resultado.stdout, end="")
            self._responder_json(200, "¡Hoja generada y enviada!")
        else:
            print(resultado.stdout, resultado.stderr, sep="", end="", file=sys.stderr)
            self._responder_json(500, "Error al generar la hoja (mira la consola del servidor).")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("-p", "--puerto", type=int, default=8000,
                        help="puerto en el que escuchar (por defecto 8000)")
    args = parser.parse_args()
    CARPETA_PDFS.mkdir(parents=True, exist_ok=True)

    # 0.0.0.0 para que se pueda abrir desde otros dispositivos de la red (móvil, tablet).
    servidor = ThreadingHTTPServer(("0.0.0.0", args.puerto), Manejador)
    print(f"Servidor en http://localhost:{args.puerto}  (Ctrl+C para parar)")
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor detenido.")


if __name__ == "__main__":
    main()
