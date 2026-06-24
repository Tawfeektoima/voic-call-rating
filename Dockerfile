FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV HOME=/home/app
ENV TMPDIR=/tmp

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg git build-essential clamav clamav-daemon clamav-freshclam \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

RUN groupadd --gid 10001 app \
    && useradd --uid 10001 --gid app --create-home --home-dir /home/app --shell /usr/sbin/nologin app \
    && mkdir -p /app/uploads /tmp /var/tmp /var/lib/call-rating/quarantine /var/lib/call-rating/accepted /var/lib/call-rating/rejected /var/lib/call-rating/state \
    && chown -R app:app /app /home/app /tmp /var/tmp /var/lib/call-rating \
    && chown -R clamav:clamav /var/lib/clamav /run/clamav

COPY --chown=app:app . .

USER app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
