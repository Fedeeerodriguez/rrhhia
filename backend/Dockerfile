FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1     PYTHONDONTWRITEBYTECODE=1     PIP_NO_CACHE_DIR=1     DATABASE_URL=sqlite:////datos/rrhhia.db

WORKDIR /app

# Las dependencias en su propia capa: cambiar codigo no reinstala todo.
COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY . .

# La base vive en un volumen, no en la imagen: reconstruir no borra los datos.
RUN mkdir -p /datos && useradd -m -u 1000 rrhhia && chown -R rrhhia /datos /app
USER rrhhia

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3     CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/salud', timeout=4).status == 200 else 1)"

# seed.py sin --reset es idempotente: siembra la primera vez y despues respeta
# lo que haya. Asi el contenedor arranca con la demo poblada.
# El seed carga datos/semilla.sql la primera vez y despues respeta lo que haya.
# Si algo falla al sembrar, la API arranca igual: un tablero vacio se puede
# poblar; un contenedor que no levanta deja la demo muerta.
CMD ["sh", "-c", "python seed.py || echo 'seed omitido'; exec uvicorn main:app --host 0.0.0.0 --port 8000"]
