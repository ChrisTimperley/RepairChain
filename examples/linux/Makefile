DOCKER_BUILDER_IMAGE_NAME=repairchain/linux:builder
DOCKER_FINAL_IMAGE_NAME=repairchain/linux

all: init docker

init:
	git submodule update --init --recursive cp-repo
	poetry run kaskara clang install

docker: init
	make -C cp-repo cpsrc-prepare
	DOCKER_BUILDKIT=1 DOCKER_IMAGE_NAME=${DOCKER_BUILDER_IMAGE_NAME} make -C cp-repo docker-build
	DOCKER_IMAGE_NAME=${DOCKER_BUILDER_IMAGE_NAME} make -C cp-repo docker-config-local
	docker build -t ${DOCKER_FINAL_IMAGE_NAME} \
		--build-arg LOCAL_USER=$(id -u) \
		--build-arg BASE_IMAGE=${DOCKER_BUILDER_IMAGE_NAME} \
		.

.PHONY: docker
