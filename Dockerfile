FROM python:3.6.9-stretch

SHELL ["/bin/bash", "-c"]

RUN mkdir /build
WORKDIR /build

COPY requirements.txt .
COPY environment .
COPY Makefile .

RUN source environment \
    && make virtualenv \
    && source .venv/bin/activate \
    && make requirements \
    && rm environment requirements.txt Makefile

ENV VIRTUAL_ENV /build/.venv
ENV PATH $VIRTUAL_ENV/bin:$PATH

ENTRYPOINT ["cellxgene"]
