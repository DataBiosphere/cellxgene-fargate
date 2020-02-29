FROM python:3.6.9-slim-stretch
SHELL ["/bin/bash", "-c"]

RUN mkdir /build
COPY . /build
WORKDIR /build

RUN pip install --upgrade pip && pip install -Ur requirements.txt

ENTRYPOINT ["./run.sh"]
