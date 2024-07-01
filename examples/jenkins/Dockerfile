ARG BASE_IMAGE
FROM ${BASE_IMAGE}

# copy source code into the container
COPY cp-repo/src /src

# pass the local user ID into the image to avoid permissions issues
ARG LOCAL_USER

# copy payload for debugging
COPY ./cp-repo/exemplar_only/cpv_exemplar/blobs/sample_solve.bin /payload.bin

RUN /usr/local/sbin/container_scripts/cmd_harness.sh build

# we need to bake kaskara-spoon into the image
COPY --from=christimperley/kaskara:spoon /opt/kaskara-spoon /opt/kaskara-spoon
