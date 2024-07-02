ARG BASE_IMAGE
FROM ${BASE_IMAGE}

# install bear into the image
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        bear

# copy source code into the container
COPY cp-repo/src /src

# pass the local user ID into the image to avoid permissions issues
ARG LOCAL_USER
ENV LOCAL_USER=${LOCAL_USER}

# NOTE I'm simulating the behavior of image-extender here
RUN cd /src \
 && bear -- /usr/local/sbin/container_scripts/cmd_harness.sh build

# NOTE this is here purely for ease of debugging
COPY ./cp-repo/exemplar_only/blobs/sample_solve.bin /work/repair/blobs/sample_solve.bin

# we also need to bake kaskara-clang into the image
COPY --from=christimperley/kaskara:cpp /opt/kaskara /opt/kaskara
