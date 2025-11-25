FROM python:3.11-slim

# Установка системных зависимостей для Pillow
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Установка рабочей директории
WORKDIR /app

# Копируем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем все файлы проекта
COPY . .

# Создаём папки для загрузок
RUN mkdir -p uploads/signatures uploads/pdfs instance

# Указываем команду запуска
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:create_app()"]