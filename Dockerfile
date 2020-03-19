FROM python:3.6.9-stretch

ARG CELLXGENE_VERSION

SHELL ["/bin/bash", "-c"]

RUN mkdir /build
WORKDIR /build

COPY requirements.txt .
COPY common.mk .
COPY Makefile .

ENV project_root /build
ENV CELLXGENE_VERSION=${CELLXGENE_VERSION}

RUN make virtualenv \
    && source .venv/bin/activate \
    && make requirements \
    && rm requirements.txt common.mk Makefile

ENV VIRTUAL_ENV /build/.venv
ENV PATH $VIRTUAL_ENV/bin:$PATH

ENTRYPOINT ["cellxgene"]
