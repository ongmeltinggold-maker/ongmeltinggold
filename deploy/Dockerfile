# ระบบร้านทอง ONG หลอมทอง — production image (Django + gunicorn + WeasyPrint)
FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DJANGO_SETTINGS_MODULE=config.settings

# system libs: WeasyPrint (pango/cairo/gdk-pixbuf), ฟอนต์ไทย, libpq, gettext, curl(healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpango-1.0-0 libpangocairo-1.0-0 libcairo2 libgdk-pixbuf-2.0-0 \
        libffi8 shared-mime-info fonts-thai-tlwg fontconfig \
        libpq5 gettext curl \
    && rm -rf /var/lib/apt/lists/* \
    && fc-cache -f

WORKDIR /app

# ติดตั้ง dependencies ก่อน (cache layer)
COPY requirements.txt .
RUN pip install -r requirements.txt

# คัดลอกโค้ดโปรเจกต์
COPY . .

# entrypoint (migrate + collectstatic + gunicorn)
RUN chmod +x deploy/entrypoint.sh \
    && (chmod +x deploy/scripts/*.sh || true) \
    && adduser --disabled-password --gecos "" appuser \
    && mkdir -p /app/staticfiles /app/media \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

ENTRYPOINT ["deploy/entrypoint.sh"]
# shell-form เพื่อให้ ${PORT} ขยายค่า (Railway/Render ใส่ PORT มาให้; ถ้าไม่มีใช้ 8000)
CMD gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} \
    --workers ${WEB_CONCURRENCY:-3} --timeout 120 --access-logfile - --error-logfile -
