DOCKER_BUILDER_IMAGE_NAME=repairchain/mock-cp:builder
DOCKER_FINAL_IMAGE_NAME=repairchain/mock-cp

docker:
	make -C mock-cp-src cpsrc-prepare
	DOCKER_BUILDKIT=1 DOCKER_IMAGE_NAME=${DOCKER_BUILDER_IMAGE_NAME} make -C mock-cp-src docker-build
	DOCKER_IMAGE_NAME=${DOCKER_BUILDER_IMAGE_NAME} make -C mock-cp-src docker-config-local
	docker build -t ${DOCKER_FINAL_IMAGE_NAME} \
		--build-arg BASE_IMAGE=${DOCKER_BUILDER_IMAGE_NAME} \
		.

.PHONY: docker
