ARG BASE_IMAGE
FROM ${BASE_IMAGE}
COPY mock-cp-src/src /src
ARG LOCAL_USER
RUN /usr/local/sbin/container_scripts/cmd_harness.sh build

# NOTE for now, we copy the payload directly into the image
# later on, we will either need to bake the payload into the image or use
# volume mounting (via /work)
COPY ./mock-cp-src/exemplar_only/cpv_1/blobs/sample_solve.bin /work/repair/blobs/sample_solve.bin
