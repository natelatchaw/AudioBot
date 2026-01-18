# NOTE: TOKEN environment variable must be provided via --env to the Docker run command

# Get the Deno binary
FROM denoland/deno:bin-2.6.5 AS deno_installer

FROM python:3.12-slim

# Update APT
RUN ["apt-get", "update", "-y"]

# Install git
RUN ["apt-get", "install", "git", "-y"]
# Install FFmpeg
RUN ["apt-get", "install", "ffmpeg", "-y"]
# Install python
RUN ["apt-get", "install", "python3", "-y"]

# Upgrade pip
RUN ["python3", "-m", "pip", "install", "--upgrade", "pip"]

# Copy the Deno binary from the Deno installer stage into the image
COPY --from=deno_installer /deno /usr/bin/deno

# Copy requirements.txt to /tmp
COPY requirements.txt /tmp/
# Install requirements.txt
RUN ["python3", "-m", "pip", "install", "--requirement", "/tmp/requirements.txt"]

# Create the data directory
RUN ["mkdir", "-p", "/data"]
# Declare the data directory as a volume
VOLUME ["/data"]

# Create the configuration directory
RUN ["mkdir", "-p", "/config"]
# Declare the configuration directory as a volume
VOLUME ["/config"]
# Copy logging configuration to /opt
COPY logging.ini /config/

# Create components directory
RUN ["mkdir", "-p", "/opt/components"]
# Copy audio component to components directory
COPY audio.py /opt/components/
# Copy audio component's companion data to components directory
COPY audio/ /opt/components/audio

# Run the bot
CMD ["python3", "-m", "bot", "--logging", "/config/logging.ini", "--config", "/config/", "--components", "/opt/components/"]