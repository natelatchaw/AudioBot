### Build Docker Image
docker build -t <code>IMAGE_NAME</code> <code>PATH_TO_DOCKERFILE</code>

- <code>IMAGE_NAME</code>: The name to identify the image created from the Dockerfile.
- <code>PATH_TO_DOCKERFILE</code>: A path on your filesystem locating the Dockerfile to build.

### Run Docker Image
docker run -d --restart=always --name <code>CONTAINER_NAME</code> -e DISCORD_TOKEN=<code>YOUR_DISCORD_BOT_TOKEN</code> <code>IMAGE_NAME</code>

- <code>CONTAINER_NAME</code>: The name to identify the container created from your Docker image.
- <code>YOUR_DISCORD_BOT_TOKEN</code>: The token provided by the Discord Developer Portal. DO NOT SHARE THIS WITH ANYONE.
- <code>IMAGE_NAME</code>: The name of the image created in the [Build](#build-docker-image) step.