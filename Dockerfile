FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY northstar ./northstar
COPY web ./web
USER 65534:65534
EXPOSE 8080
CMD ["python", "-m", "northstar", "--host", "0.0.0.0", "--port", "8080"]
