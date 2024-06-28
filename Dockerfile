ARG BASE_IMAGE=ubuntu:noble-20240530
ARG INSTALL_TO=/opt/repairchain

FROM ${BASE_IMAGE} AS builder
ARG DEBIAN_FRONTEND=noninteractive
ENV LANG C.UTF-8
ENV LC_ALL C.UTF-8

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        autoconf \
        libtool \
        apt-transport-https \
        build-essential \
        ca-certificates \
        curl \
        g++ \
        gcc \
        git \
        libboost-all-dev \
        libbz2-dev \
        libffi-dev  \
        liblzma-dev \
        libncursesw5-dev \
        libreadline-dev \
        libsqlite3-dev  \
        libssl-dev \
        libxml2-dev \
        libxmlsec1-dev \
        tk-dev \
        vim \
        wget \
        xz-utils \
        zlib1g-dev \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

ARG PYENV_VERSION="2.4.1"
RUN git clone https://github.com/pyenv/pyenv.git /tmp/pyenv \
 && cd /tmp/pyenv \
 && git checkout "v${PYENV_VERSION}" \
 && cd plugins/python-build \
 && ./install.sh \
 && rm -rf /tmp/pyenv

ARG PYTHON_VERSION=3.12.3
RUN python-build "${PYTHON_VERSION}" /usr/local

ARG POETRY_VERSION=1.8.3
RUN pip install --no-cache-dir poetry==${POETRY_VERSION}

ARG INSTALL_TO
COPY . /tmp/repairchain
WORKDIR /tmp/repairchain
RUN make install \
 && make bundle \
 && mkdir -p "${INSTALL_TO}/bin" \
 && mv ./dist/repairchain "${INSTALL_TO}/bin"

FROM ${BASE_IMAGE} as runtime
ARG DEBIAN_FRONTEND=noninteractive
ENV LANG C.UTF-8
ENV LC_ALL C.UTF-8
ARG INSTALL_TO
COPY --from=builder ${INSTALL_TO} ${INSTALL_TO}
