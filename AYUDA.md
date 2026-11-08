# Ayuda del proyecto «multiplicaciones»

Referencia técnica: qué hace cada fichero, cada constante y cada función.
Para saber qué es el proyecto, cómo se instala y cómo se usa, mira el
**[README.md](README.md)**.

Las tablas que se pasan como argumento solo deciden qué multiplicaciones salen
en los problemas. La tabla de referencia del final no se puede elegir: sale
al azar (ver `elegir_tabla`).

Regla en todo el proyecto: el 0, el 1 y el 10 nunca aparecen, ni como tabla
ni como factor.

## Cómo encajan los ficheros

```
multiplicaciones.py   main(): lee los argumentos y genera las multiplicaciones «en bruto»
        │
        ├── generacion_pdf.py   convierte las multiplicaciones en problemas y crea el PDF
        │         └── situaciones.py   datos: objetos, relaciones y plantillas de frases
        │
        └── enviar_email.py     envía el PDF por correo (opción -e)

servidor.py + index.html   página web que ejecuta «multiplicaciones.py -e»
```

---

## `multiplicaciones.py`

Es el programa principal. Solo contiene `main` y la generación de las
multiplicaciones «en bruto», es decir, los números y no el texto.

### Constantes

| Nombre | Para qué sirve |
|---|---|
| `ASUNTO_EMAIL`, `TEXTO_EMAIL` | Asunto y texto del correo que se envía con `-e`. |
| `NUM_EJERCICIOS` | Número de problemas de la hoja (10). |
| `NUMEROS_VALIDOS` | Números permitidos como tabla y como factor: del 2 al 9. |
| `FICHERO_TABLAS_SALIDAS` | Fichero `tablas_salidas.json`, donde se apuntan las tablas de referencia que ya han salido. Se crea en la carpeta desde la que se ejecuta el programa, que es la misma de los PDF. |

### Funciones

| Función | Qué hace |
|---|---|
| `fix_adjacent_dups(items)` | Reordena la lista para que no haya dos elementos iguales seguidos, siempre que se pueda. Cambia la lista directamente y no devuelve nada. |
| `generar_lineas(tablas, num_ejercicios)` | Crea las parejas `(tabla, factor)` de los problemas, por ejemplo `(7, 4)`. Combina las tablas pedidas con los factores del 2 al 9 y elige al azar sin repetir. Solo repite cuando no hay bastantes combinaciones distintas. Al final llama a `fix_adjacent_dups`. |
| `leer_tablas_salidas()` | Lee `tablas_salidas.json` y devuelve la lista de tablas que ya han salido en la ronda actual. Si el fichero no existe o está estropeado, devuelve una lista vacía y empieza una ronda nueva. |
| `guardar_tablas_salidas(salidas)` | Guarda esa lista en `tablas_salidas.json`. |
| `elegir_tabla()` | Elige al azar la tabla de referencia del final de la hoja, solo entre las que aún no han salido. Cuando han salido las 8, empieza una ronda nueva, y la primera tabla de esa ronda nunca es la última que salió. Devuelve `(tabla, salidas)`: la tabla elegida y la lista que hay que guardar. |
| `parsear_tablas(valores, parser)` | Comprueba las tablas escritas en la línea de comandos. Da error si alguna no es un número entero o no está entre el 2 y el 9. Quita las repetidas y, si no se indica ninguna, devuelve todas. |
| `main(argv=None)` | Función principal. Lee los argumentos (tablas, `-o` y `-e`) y comprueba que las direcciones de correo tengan `@`. Después valida los datos, prepara los emojis, genera las parejas, elige la tabla, crea el PDF y guarda la tabla elegida. Si se usó `-e`, envía el PDF por correo. |

---

## `generacion_pdf.py`

Convierte las parejas de números en problemas con texto y escribe el PDF.

### Constantes (ajustes del aspecto)

| Nombre | Para qué sirve |
|---|---|
| `FONTE_TEXTO` | Fuente del texto. Puede ser una fuente estándar de PDF (`"Helvetica"`…) o un `.ttf` de la carpeta `fonts/`. |
| `TAMANO_TEXTO` | Tamaño de la letra. El interlineado, los emojis y la línea de respuesta se ajustan solos a este tamaño. |
| `SEPARACION_EJERCICIOS` | Espacio en blanco entre un problema y el siguiente. |
| `TITULO_CABECERA`, `TEXTO_CABECERA` | Título e introducción del principio de la hoja. Si se dejan en `""`, no aparecen. |
| `TITULO_TABLA` | Título de la tabla de referencia (`"Tabla del {tabla}"`). |
| `TAMANO_TABLA`, `COLOR_FONDO_TABLA`, `COLOR_BORDE_TABLA` | Tamaño de la letra y colores de la tabla de referencia. |
| `ALTURA_CIFRAS` | Alto de las cifras en proporción a la letra (0,70 en Fredoka). Sirve para centrar los números en vertical en cada fila de la tabla. Si cambias de fuente y los números quedan altos o bajos, ajústalo: más alto los baja, más bajo los sube. |
| `CARPETA_SCRIPT`, `CARPETA_EMOJIS`, `URL_TWEMOJI`, `TAMANO_EMOJI` | Dónde están las imágenes de los emojis, de dónde se descargan y a qué tamaño se dibujan. |
| `PREFIJO_PDF`, `PATRON_NUMERO_PDF` | Sirven para poner nombre a los PDF y numerarlos. |
| `RELACIONES_POR_CONTEXTO`, `PLANTILLAS_POR_CONTEXTO`, `CONTEXTOS` | Agrupan por contexto las relaciones y plantillas de `situaciones.py`. Así cada problema combina una relación y una frase que encajan. |

### Funciones: enunciados

| Función | Qué hace |
|---|---|
| `datos_objeto(id_objeto)` | Devuelve `(singular, plural, género, emoji)` de un objeto de `OBJETOS`. Si el objeto no tiene emoji, el emoji es `""`. Da error si el objeto no tiene 3 o 4 datos. |
| `validar_datos()` | Se ejecuta al arrancar. Comprueba que todos los objetos están bien escritos, que las relaciones usan objetos que existen y que cada contexto tiene al menos una plantilla. |
| `mostrar_salida(lineas, tabla, factores, ruta_pdf)` | Convierte cada pareja en un problema: elige al azar contexto, relación y plantilla, y rellena los números, los nombres en singular y plural y «Cuántos/Cuántas». Los emojis solo se ponen antes del `¿`, para que la pregunta se lea limpia. Después llama a `generar_pdf` con los problemas y la tabla de referencia. Es el único punto de salida del programa. |

### Funciones: emojis

reportlab no sabe dibujar emojis a color, así que cada emoji se sustituye
por una imagen PNG de Twemoji.

| Función | Qué hace |
|---|---|
| `nombre_twemoji(emoji)` | Calcula el nombre del PNG de Twemoji: los códigos del emoji en hexadecimal, unidos por `-`. |
| `emojis_usados()` | Devuelve todos los emojis que aparecen en `OBJETOS`. |
| `ruta_emoji(emoji)` | Devuelve la ruta del PNG de un emoji dentro de `emojis/`. |
| `preparar_emojis()` | Descarga de internet los PNG que falten en `emojis/`. Solo usa la red la primera vez que se añade un emoji nuevo. |
| `marcar_emojis(texto)` | Cambia cada emoji del texto por una etiqueta `<img>` con su PNG, del tamaño adecuado y alineada con la letra. |

### Funciones: PDF

| Función | Qué hace |
|---|---|
| `registrar_fuente(fuente)` | Prepara la fuente para reportlab. Las fuentes estándar se devuelven tal cual. Los `.ttf` se registran y se usa el mismo fichero también como negrita, para que funcione el número del ejercicio en negrita. |
| `tabla_multiplicar_pdf(tabla, factores, fuente)` | Crea el bloque de la tabla de referencia: el título y un cuadro con las filas `tabla x factor = resultado`, en columnas alineadas. El bloque nunca se parte entre dos páginas. |
| `generar_pdf(ejercicios, tabla, factores, ruta_pdf)` | Monta el PDF en A4: la cabecera, cada problema con su línea `____ x ____ = ____` y la tabla de referencia al final. |
| `nombre_pdf_automatico(carpeta)` | Si no se usa `-o`, da el nombre del PDF: `multiplicaciones_<día-mes>_<hora>_<año>_<número>.pdf`. El número es uno más que el más alto que ya haya en la carpeta. |

---

## `situaciones.py`

Solo contiene datos, sin funciones. Para dar más variedad a los problemas,
basta con añadir entradas aquí.

| Estructura | Contenido |
|---|---|
| `OBJETOS` | `id: (singular, plural, género "m"/"f"[, emoji])`. El emoji es opcional. |
| `RELACIONES` | `(contexto, id_a, id_b)`: A es el número de grupos y B la cantidad que hay en cada grupo. La respuesta siempre es A × B, en la unidad de B. |
| `PLANTILLAS` | `(contexto, frase)`: una frase solo se usa con relaciones de su mismo contexto. Huecos disponibles: `{a} {b} {a_singular} {a_plural} {b_singular} {b_plural} {a_cuantos} {b_cuantos}`. No se pueden escribir llaves `{}` sueltas en una frase. |

---

## `enviar_email.py`

Envía el PDF por correo (SMTP de Brevo). Los datos privados (servidor,
puerto, tipo de seguridad, usuario, contraseña, remitente y `DESTINATARIOS`
por defecto) **no están en el código**: se leen del fichero `.env` de la
carpeta del proyecto, que no se sube a git. En un ordenador nuevo hay que
copiar el `.env` de otro ordenador, o copiar `.env.ejemplo` como `.env` y
rellenarlo. Si una variable ya existe en el entorno (por ejemplo en Docker),
tiene prioridad sobre el `.env`.

| Función | Qué hace |
|---|---|
| `cargar_env(ruta)` | Lee las líneas `CLAVE=valor` del `.env` y las pasa a variables de entorno, sin pisar las que ya existan. Se ejecuta al importar el módulo. Si el `.env` no existe, no hace nada. |
| `crear_mensaje(destinatarios, asunto, texto, ruta_pdf)` | Construye el correo con remitente, destinatarios, asunto y texto, y el PDF adjunto. |
| `comprobar_configuracion()` | Comprueba que estén rellenos los datos del servidor, el usuario, la contraseña y el remitente, y que `SEGURIDAD` sea `"tls"` o `"ssl"`. Si falta algo, termina con un mensaje claro. |
| `enviar_pdf(destinatarios, asunto, texto, ruta_pdf)` | Envía el correo. Si no se indican destinatarios, usa `DESTINATARIOS`. Se conecta con SSL o STARTTLS según `SEGURIDAD` y avisa si falla la contraseña o la conexión. |

---

## `servidor.py`

Servidor web sencillo, sin dependencias externas. Muestra `index.html`, que
tiene un botón «Generar». Al pulsarlo, se crea la hoja y se envía por correo.

| Nombre | Qué hace |
|---|---|
| `CARPETA_PDFS` | Carpeta donde se guardan los PDF y `tablas_salidas.json`. Se puede cambiar con la variable de entorno `CARPETA_PDFS`; por defecto es la carpeta del proyecto. |
| `ESPERA_SEGUNDOS` | Segundos que hay que esperar entre una hoja y la siguiente, para no mandar muchos correos por error. |
| `segundos_restantes()` | Devuelve los segundos que faltan para poder generar otra hoja (0 si ya se puede). |
| `Manejador` | Clase que atiende las peticiones de la web. |
| `Manejador._responder(codigo, tipo, cuerpo)` | Envía una respuesta HTTP con su código, su tipo de contenido y su cuerpo. |
| `Manejador._responder_json(codigo, mensaje)` | Responde con un JSON que lleva el mensaje y `espera`, los segundos que faltan. La página usa `espera` para la cuenta atrás del botón. |
| `Manejador.do_GET()` | Devuelve la página `index.html`, o un 404 si se pide otra dirección. |
| `Manejador.do_POST()` | Atiende `/generar`. Si ya se está generando una hoja, responde 409. Si aún no ha pasado la espera, responde 429. Si no, ejecuta `multiplicaciones.py -e` en `CARPETA_PDFS`, con un límite de 120 s, e informa de si ha ido bien. |
| `main()` | Lee el puerto (`-p`, por defecto 8000) y arranca el servidor para toda la red local. Se para con Ctrl+C. |

---

## Otros ficheros

| Fichero | Qué es |
|---|---|
| `index.html` | La página web con el botón «Generar» y la cuenta atrás. |
| `Dockerfile`, `docker-compose.yml` | Sirven para ejecutar el servidor en Docker (`docker compose up -d --build`, puerto 8000). Los PDF y `tablas_salidas.json` se guardan en `/app/pdfs`, dentro del contenedor, y se pierden al recrearlo. La contraseña no va en la imagen: `docker-compose.yml` pasa el `.env` al contenedor al arrancar. |
| `fonts/` | Fuente `Fredoka-SemiBold.ttf` y su licencia `OFL-Fredoka.txt`. Es una fuente libre (SIL Open Font License), así que se puede subir a git y redistribuir siempre que vaya acompañada de su licencia. Es una versión estática (peso 600) creada a partir de la fuente variable de Google Fonts. |
| `emojis/` | Imágenes PNG de Twemoji (licencia CC-BY 4.0). |
| `tablas_salidas.json` | Se crea solo. Guarda las tablas de referencia que ya han salido en la ronda actual. Si lo borras, empieza una ronda nueva. Se sincroniza con git a propósito, para compartir la rotación entre ordenadores. |
| `.env` | Datos privados del correo, incluida la contraseña. **No se sube a git**: hay que copiarlo a mano a cada ordenador. |
| `.env.ejemplo` | Plantilla del `.env`, sin datos reales. Sí se sube a git. |
| `.gitignore` | Lo que git no sincroniza: `.env`, `env/`, `__pycache__/`, y los PDF. |
| `.dockerignore` | Lo que no se envía a Docker al construir la imagen. |
| `README.md` | Portada del repositorio: qué es, instalación, uso y licencias. |
| `docs/ejemplo.png` | Captura de una hoja de ejemplo que aparece en el README. Hay que regenerarla a mano si cambia mucho el aspecto de la hoja. |
| `CLAUDE.md` | Notas técnicas del proyecto para Claude Code. |
