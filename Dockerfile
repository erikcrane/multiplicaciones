FROM python:3.12-slim

# tzdata para que la hora de los nombres de los PDF sea la local (ver TZ en docker-compose.yml).
RUN apt-get update \
    && apt-get install -y --no-install-recommends tzdata \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir reportlab==5.1.0

WORKDIR /app
COPY multiplicaciones.py generacion_pdf.py situaciones.py enviar_email.py servidor.py index.html ./
COPY fonts/ fonts/
COPY emojis/ emojis/

# Carpeta de los PDF, dentro del contenedor (se pierden al recrearlo). Con
# permisos para cualquier usuario, porque el contenedor no corre como root
# (ver "user:" en docker-compose.yml).
RUN mkdir -p /app/pdfs && chmod 777 /app/pdfs

ENV PYTHONUNBUFFERED=1 \
    CARPETA_PDFS=/app/pdfs

EXPOSE 8000
CMD ["python", "servidor.py"]
