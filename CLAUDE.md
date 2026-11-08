# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Small Python CLI that generates a PDF worksheet of 10 dog-themed multiplication word problems (in Spanish). Code, comments, identifiers and output are all in Spanish — keep new code consistent with that.

## Commands

A uv-created virtualenv lives in `env/` (Python 3.12; dependency: `reportlab`, installed with `uv pip install --python env/bin/python ...`). The emoji folder is resolved relative to the script, so it can be run from any directory. There is no requirements file, build step, linter config or test suite.

```bash
env/bin/python multiplicaciones.py                 # all tables (2..9) -> multiplicaciones_DD-MM_HHhMM_YYYY_NNN.pdf
env/bin/python multiplicaciones.py 3 6 9           # only tables 3, 6, 9
env/bin/python multiplicaciones.py 3 6 9 -o x.pdf  # custom output path
env/bin/python multiplicaciones.py -e a@x.com      # also email the PDF via SMTP (-e repeatable)
env/bin/python multiplicaciones.py 3 6 -e         # -e without address -> DESTINATARIOS in .env (put it after the tables)
```

## Architecture

Four modules:

- `situaciones.py` — pure data, no logic. Three structures:
  - `OBJETOS`: `id -> (singular, plural, gender "m"/"f"[, emoji])` (emoji optional: drop the 4th element; `None` is not accepted).
  - `RELACIONES`: `(contexto, id_a, id_b)` — A is the number of groups, B the quantity per group; the answer is always A × B in B's unit.
  - `PLANTILLAS`: `(contexto, template)` — a template is only paired with relations of the same `contexto`. Placeholders: `{a} {b} {a_singular} {a_plural} {b_singular} {b_plural} {a_cuantos} {b_cuantos}` (the `_cuantos` ones resolve to "Cuántos"/"Cuántas" by gender). Templates go through `str.format`, so no literal braces.
  - Adding variety = adding entries here; `validar_datos()` checks at startup that relations reference existing objects and every context has a template.
- `multiplicaciones.py` — only `main()` and the "raw" multiplication generation (no text/PDF code here). Pipeline in `main()`:
  1. `parsear_tablas` validates args (only 2–9, duplicates dropped, empty → all tables).
  2. `generar_lineas` builds `(tabla, factor)` pairs from tables × `NUMEROS_VALIDOS` (2..9, also the default tables and the allowed table args), sampling without repetition when possible, otherwise repeating the pool; `fix_adjacent_dups` avoids identical consecutive pairs.
  3. `elegir_tabla` picks the reference table printed (solved) at the end of the sheet. It ignores the table args and rotates through all of 2..9: the tables already used in the current round are persisted in `tablas_salidas.json` in the current directory (next to the PDFs; in Docker `/app/pdfs`, so lost on recreate), none repeats until all have appeared, and a new round never starts with the last one. `main` saves the state with `guardar_tablas_salidas` only after the PDF is built.
- `generacion_pdf.py` — everything about turning the pairs into word problems and the PDF:
  1. `mostrar_salida(lineas, tabla, factores, ruta_pdf)` picks a random context → relation → template per pair and formats the statement. Emojis are appended to nouns only in the part of the template before the first `¿`; the question is formatted with plain nouns. It is the deliberate single output seam (so the destination can be swapped later); it calls `generar_pdf`.
  2. `generar_pdf` renders with reportlab platypus. Text font is `FONTE_TEXTO`: either a standard PDF font name or a `.ttf` path relative to the script (currently `fonts/Fredoka-SemiBold.ttf`: SIL OFL, license in `fonts/OFL-Fredoka.txt`, tracked in git. It is a static weight-600 instance made with fontTools `instancer` from Google Fonts' variable `Fredoka[wdth,wght].ttf`, because reportlab only uses the default instance of variable fonts. Only use fonts whose license allows redistribution. reportlab embeds a subset of TTFs in the PDF, so recipients don't need the font installed). `registrar_fuente` registers TTFs and maps their bold variant to the same file, because `<b>` on the exercise number fails for a TTF without a registered family (answer lines Courier-Bold). The sheet starts with a header built from `TITULO_CABECERA` (centered, 1.6× size) and `TEXTO_CABECERA` (justified intro); either can be set to `""` to omit it. After the exercises comes the reference table from `tabla_multiplicar_pdf` (title `TITULO_TABLA`, a reportlab `Table` of `tabla x factor = resultado` rows, size `TAMANO_TABLA`; cells get `LEADING = TAMANO_TABLA * (2 - ALTURA_CIFRAS)` with zero top/bottom padding so digits are vertically centered — reportlab centers by leading, which defaults to 12 regardless of FONTSIZE; `ALTURA_CIFRAS` is the font's digit height ratio, 0.70 for Fredoka (measured from glyph bounds; change it with the font); colors `COLOR_FONDO_TABLA`/`COLOR_BORDE_TABLA`, wrapped in `KeepTogether` so it is never split across pages). Layout knobs at the top of the module: `TAMANO_TEXTO` (font size; leading, emoji size/offset and answer line scale from it) and `SEPARACION_EJERCICIOS` (gap between exercises). reportlab can't render color emoji fonts, so `marcar_emojis` replaces each emoji from `OBJETOS` with an inline `<img>` of its Twemoji PNG (72x72, CC-BY 4.0). The PNGs live in `emojis/` (path resolved from the script's directory), named by Twemoji's rule (hex codepoints joined by `-`, `FE0F` dropped unless the sequence has a ZWJ); `preparar_emojis()` downloads any missing ones from the jsDelivr CDN (pinned `jdecked/twemoji@17.0.3`) on startup, so network is only needed the first time a new emoji is added. Emojis outside `OBJETOS` are not replaced and would render badly in Helvetica.

- `enviar_email.py` — sends the PDF through SMTP (stdlib `smtplib`, Brevo `smtp-relay.brevo.com`). Server, port, user, password, `SEGURIDAD` (`tls` = STARTTLS / `ssl` = implicit SSL), sender and default `DESTINATARIOS` (comma-separated) are read **only** from one file, `fichero_env()`: `RUTA_SECRETO` (`/run/secrets/multiplicaciones_env`, the Docker secret holding the whole multi-line .env, which is how it is deployed, also in Portainer) if it exists, else `.env` in the project dir (gitignored, secret; template `.env.ejemplo`). Environment variables are deliberately neither read nor written (`cargar_env` returns a dict), so stale shell variables with the same generic names can't hijack the config. A missing/unreadable file is a hard error (`sys.exit`). The file is only read with `-e`: `main` calls `preparar_envio(direcciones)` right after parsing args, before generating anything (so a broken config creates no PDF and doesn't consume a table of the rotation), and later passes its `(configuracion, destinatarios)` to `enviar_pdf`. Never put credentials back into the code. Subject/body are `ASUNTO_EMAIL`/`TEXTO_EMAIL` at the top of `multiplicaciones.py`.

- `servidor.py` + `index.html` — stdlib `http.server` web UI: one "Generar" button that POSTs `/generar`, which runs `multiplicaciones.py -e` with cwd `CARPETA_PDFS` (env var, default the project dir). Button size knobs are marked in the `#generar` CSS. After each run (success or failure) the server refuses new runs for `ESPERA_SEGUNDOS` (429) to avoid repeated emails; every JSON response carries `espera` (seconds left), which the page shows as a countdown on the button. `env/bin/python servidor.py [-p PORT]` (default 8000).
- Docker: `Dockerfile` + `docker-compose.yml` (`docker compose up -d --build`), port 8000, PDFs kept inside the container in `/app/pdfs` (no volume, lost on recreate; created world-writable in the Dockerfile), `TZ=Europe/Madrid`, runs as uid 1000. Meant to sit behind Nginx Proxy Manager on the LAN. The SMTP settings reach the container as the compose secret `multiplicaciones_env` (`file: ./.env`; in Portainer an absolute host path), never via env vars or the image; non-swarm secrets are bind mounts, so the file must be readable by uid 1000.
- Git: `.gitignore` excludes `.env`, `env/`, `__pycache__/`, and `*.pdf`. `tablas_salidas.json` is deliberately tracked so the table rotation is shared between computers.

Without `-o`, `nombre_pdf_automatico()` (in `generacion_pdf.py`) names the output `multiplicaciones_<DD-MM>_<HHhMM>_<YYYY>_<NNN>.pdf` in the current directory, where NNN is one more than the highest number already present there (never resets).

Docs: `README.md` (landing page: what it is, install, usage, sync, third-party licenses; shows `docs/ejemplo.png`, a screenshot regenerated by hand) and `AYUDA.md` (per-file/per-function reference in Spanish). Keep both in sync when changing functions, constants, commands or setup.

Domain rule enforced throughout: 0, 1 and 10 never appear, neither as table nor as factor.
