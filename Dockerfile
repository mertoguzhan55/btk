# Temel imaj: Python 3.11 slim
FROM python:3.11-slim

# Sistem güncellemeleri ve temel kütüphaneler
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Çalışma dizini
WORKDIR /app

# pip güncelle
RUN pip install --upgrade pip

# Gereksinimleri yükle
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Uygulama dosyalarını kopyala
COPY . .

# .env dosyasını okuma için dotenv yüklenmiş olmalı (requirements.txt'de olmalı)
# Uygulama başlatma komutu (örnek olarak uvicorn ile FastAPI)
CMD ["python", "app.py", "--env", "local"]
