FROM python:3.7.0

WORKDIR /usr/src/app

RUN apt-get update && apt-get upgrade -y
RUN pip install --upgrade pip
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir --force-reinstall -r requirements.txt

COPY . /usr/src/app/

