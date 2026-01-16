## Docker

### Build Docker Image
Start by building the docker image.
> docker build -t <code>IMAGE_NAME</code> <code>PATH_TO_DOCKERFILE</code>

- <code>IMAGE_NAME</code>: The name to identify the image created from the Dockerfile.
- <code>PATH_TO_DOCKERFILE</code>: A path on your filesystem locating the Dockerfile to build.

### Run Docker Image
Run the docker image once it has been built.
> docker run -d --restart=always -e TOKEN=<code>YOUR_DISCORD_BOT_TOKEN</code> --name <code>CONTAINER_NAME</code> <code>IMAGE_NAME</code>

- <code>YOUR_DISCORD_BOT_TOKEN</code>: The token provided by the Discord Developer Portal. DO NOT SHARE THIS WITH ANYONE.
- <code>CONTAINER_NAME</code>: The name to identify the container created from your Docker image.
- <code>IMAGE_NAME</code>: The name of the image created in the [Build](#build-docker-image) step.