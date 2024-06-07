ARG BASE_IMAGE=ubuntu:noble-20240530
FROM ${BASE_IMAGE}

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        build-essential \
        git

# TODO copy Kaskara portable installation into image due to restrictions of the competition

# TODO compile to a portable binary via PyInstaller
