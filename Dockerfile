FROM python:3.6-slim

LABEL maintainer="Sergey jr. Bakaleynik"

WORKDIR /app

COPY templates/ /app/templates

COPY requirements.txt /app/

COPY gdriveloader.py /app/

COPY app.py /app/

COPY client_id.json /app/

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

ENV GAPP_SECRET b'\xc4` \xae\xd4\x89\x1a9\xd5\x05\xc9RK\xed\xb2G'

EXPOSE 8080

ENTRYPOINT ["python3", "app.py"]
