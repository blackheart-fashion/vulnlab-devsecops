# VulnLab - training target container
FROM python:3.11-slim

# iputils-ping needed so the intentional command-injection demo (/ping) works
RUN apt-get update && apt-get install -y --no-install-recommends \
    iputils-ping \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/uploads

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
  CMD python -c "import urllib.request,sys; sys.exit(0) if urllib.request.urlopen('http://127.0.0.1:5000/healthz').status==200 else sys.exit(1)"

# gunicorn for a more "real" deployment feel; app.py also runnable directly for local debug
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "app:app"]
