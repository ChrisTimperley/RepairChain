ARG BASE_IMAGE

ARG BASE_BUILD_IMAGE_UBUNTU_22=ubuntu:22.04
FROM ${BASE_BUILD_IMAGE_UBUNTU_22} AS patch-donor
ARG MAKE_JOBS=8

RUN apt-get update -y && \
    apt-get install -y \
        clang \
        make \
        xz-utils \
        wget

RUN wget https://ftp.gnu.org/gnu/patch/patch-2.7.tar.xz && \
    tar xf patch-2.7.tar.xz   && \
    cd patch-2.7 && \
    LDFLAGS="-static" ./configure && \
    make -j ${MAKE_JOBS} && \
    cp src/patch /usr/local/bin/patch


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

# we mimic the baking of "patch" into the image
COPY --from=patch-donor /usr/local/bin/patch /usr/bin/patch
