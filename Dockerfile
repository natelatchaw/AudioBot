# NOTE: DISCORD_TOKEN environment variable must be provided via --env to the Docker run command

FROM python:3.9

# Update APT
RUN ["apt-get", "update", "-y"]
# Upgrade APT
RUN ["apt-get", "upgrade", "-y"]
# Install FFmpeg
RUN ["apt-get", "install", "ffmpeg", "-y"]

# Upgrade pip
RUN ["python3", "-m", "pip", "install", "--upgrade", "pip"]

# Copy requirements.txt to /tmp
COPY requirements.txt /tmp/
# Install requirements.txt
RUN ["python3", "-m", "pip", "install", "--requirement", "/tmp/requirements.txt"]

# Copy logging configuration to /opt
COPY logging.ini /opt/

# Create components directory
RUN ["mkdir", "-p", "/opt/components"]
# Copy audio component to directory
ADD audio.py /opt/components

# Run the bot
CMD ["python3", "-m", "bot", "--logging", "/opt/logging.ini", "--components", "/opt/components"]