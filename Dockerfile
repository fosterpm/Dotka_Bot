FROM python:3.11-slim

# Устанавливаем системные зависимости, компиляторы и FFmpeg
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ffmpeg \
    gcc \
    libffi-dev \
    libopus-dev && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Копируем зависимости и устанавливаем их
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь код проекта
COPY . .

# Запускаем бота
CMD ["python", "main.py"]
