# NOTE: TOKEN environment variable must be provided via --env to the Docker run command

FROM python:3.12-slim

# Update APT
RUN ["apt-get", "update", "-y"]
# Upgrade APT
RUN ["apt-get", "upgrade", "-y"]
# Install git
RUN ["apt-get", "install", "git", "-y"]
# Install FFmpeg
RUN ["apt-get", "install", "ffmpeg", "-y"]

# Upgrade pip
RUN ["python3", "-m", "pip", "install", "--upgrade", "pip"]

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