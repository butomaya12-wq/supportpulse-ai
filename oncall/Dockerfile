FROM python:3.12-slim
WORKDIR /code
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY oncall/requirements.txt ./requirements-oncall.txt
RUN pip install --no-cache-dir -r requirements-oncall.txt
COPY oncall ./oncall
RUN mkdir -p /data
EXPOSE 8081
CMD ["uvicorn", "oncall.main:app", "--host", "0.0.0.0", "--port", "8081"]
