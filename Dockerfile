FROM python:3.11-slim

# Dependencias necesarias para Chromium + Playwright
RUN apt-get update && apt-get install -y \
    wget gnupg ca-certificates \
    libnss3 libnspr4 libxss1 libasound2 \
    libx11-xcb1 libxcomposite1 libxcursor1 libxi6 libxtst6 \
    libpangocairo-1.0-0 libxrandr2 libatk1.0-0 libatk-bridge2.0-0 libgtk-3-0 \
    fonts-noto-color-emoji fonts-unifont \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && python -m playwright install chromium

COPY . .

ENV PORT=8080
EXPOSE 8080

CMD ["bash", "-lc", "gunicorn -w 2 -b 0.0.0.0:$PORT main:app"]
