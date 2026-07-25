FROM python:3.11-slim


ENV PYTHONUNBUFFERED=1

WORKDIR /app


COPY . .


RUN pip install --no-cache-dir oci


CMD ["python", "sniper2.py"]
