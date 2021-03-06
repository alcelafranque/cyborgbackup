FROM python:3.6

ENV PYTHONUNBUFFERED 1
ENV DJANGO_ENV dev
ENV DOCKER_CONTAINER 1

COPY ./requirements.txt /cyborgbackup/requirements.txt
RUN pip install -r /cyborgbackup/requirements.txt

WORKDIR /cyborgbackup/

EXPOSE 8000
