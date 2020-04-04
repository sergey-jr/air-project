FROM python:3.6-alpine

LABEL maintainer="Sergey jr. Bakaleynik"

WORKDIR /app

COPY templates .

COPY requirements.txt .

COPY gdriveloader.py .

COPY app.py .

COPY client_id.json .

RUN pip install -r requirements.txt

ENV GAPP_SECRET b'\xc4` \xae\xd4\x89\x1a9\xd5\x05\xc9RK\xed\xb2G'

EXPOSE 8080

ENTRYPOINT ["python3", "app.py"]