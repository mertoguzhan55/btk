# 📚 BTK Akademi - Chatbot Uygulaması

Bu proje, Google Gemini API'sini kullanarak kullanıcıdan gelen verileri özetleyen ve etkileşimli hale getiren bir chatbot sistemidir.

---

## 📌 İçindekiler

- [🚀 Lokal Kurulum Rehberi](#-lokal-kurulum-rehberi)
- [🐳 Docker Compose Kurulumu](#-docker-compose-kurulum-rehberi)
- [📁 Proje Yapısı](#-proje-yapisi)
- [🛠 Destek](#-destek)


## 🚀 Lokal Kurulum Rehberi

### 🔧 1. Projeyi Klonlayın

```bash
git clone https://github.com/mertoguzhan55/btk.git
cd btk
```

### 2. Docker-compose.yaml dosyasını şu şekilde değiştirin:

```bash
version: "3.8"
services:
  postgres:
    image: postgres
    container_name: postgres-container
    restart: always
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: admin
      POSTGRES_DB: workplace
    ports:
      - "5432:5432"
    volumes:
      - postgres-data:/var/lib/postgresql/data

  pgadmin:
    image: dpage/pgadmin4
    container_name: pgadmin-container
    restart: always
    ports:
      - "8888:80"
    environment:
      PGADMIN_DEFAULT_EMAIL: admin@example.com
      PGADMIN_DEFAULT_PASSWORD: admin

volumes:
  postgres-data:

```

```bash
docker-compose up --build
```

ile database'i docker ile ayağa kaldırın.


---

### 🧪 2. `.env` Dosyasını Oluşturun

btk klasörüne girdikten sonra aşağıdaki gibi bir `.env` dosyası oluşturun:

```env
GOOGLE_API_KEY=your_google_api_key
SECRET_KEY=your_44_char_secret
```

> **GOOGLE_API_KEY**: https://aistudio.google.com/app/apikey adresinden alınmalıdır.
> **SECRET_KEY**: JWT için 44 haneli rastgele bir key üretin.

---

### ⚙️ 3. `config.local` Yapılandırmasını Güncelleyin

`configs/config.local` içindeki ayarları aşağıdaki gibi yapılandırın:

#### ✅ `json_handler` Ayarı:
```toml
[JsonHandler]
directory = "/home/.../btk/app/data"
```

#### ✅ `connection` ve `crud` Ayarları:
```toml
db_host = "localhost"
```

---

### 🐍 4. Conda Ortamını Kurun

```bash
conda create -n btk python=3.11 -y
conda activate btk
pip install -r requirements.txt
```

---

## ▶️ Çalıştırma

```bash
python app.py --env local
```

> Uygulama başarıyla çalıştığında [http://localhost:8000](http://localhost:8000) adresinden erişebilirsiniz.

---

## 📁 Proje Yapısı

```
btk/
├── app/
│   └── data/
├── configs/
│   └── config.local
├── requirements.txt
├── app.py
└── ...
```

## 🚀 Docker Compose Kurulum Rehberi

### 🧪 1- `.env` Dosyasını Oluşturun

btk klasörüne girdikten sonra aşağıdaki gibi bir `.env` dosyası oluşturun:


```env
GOOGLE_API_KEY=your_google_api_key
SECRET_KEY=your_44_char_secret
```

> **GOOGLE_API_KEY**: https://aistudio.google.com/app/apikey adresinden alınmalıdır.
> **SECRET_KEY**: JWT için 44 haneli rastgele bir key üretin.

```
docker compose up --build
```

* Docker-compose.yaml dosyasını değiştirmeyin.
* docker-compose ile ayağa kaldıracaksanız application'ı config.local dosyasında, **db_host** değerleri postgres olacak. Ancak yukarıdaki gibi lokalde çalıştıracaksanız db_host değerleri localhost olacak.

Sonrasında başarılı bir şekilde uygulama çalışacaktır.






## 🛠 Destek

Herhangi bir sorunla karşılaşırsanız lütfen bir [issue](https://github.com/mertoguzhan55/btk/issues) açın.
