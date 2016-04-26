# Get base image
FROM ubuntu:15.04

# Install the required packages
RUN apt-get update && apt-get -y install python-pip rabbitmq-server git wget clamav && pip install Flask elasticsearch pika requests && pip install -U flask-cors

# Install docker
RUN wget -qO- https://get.docker.com/ | sh

# Install sdhash
RUN wget -qO- https://raw.githubusercontent.com/BU-NU-CLOUD-SP16/Container-Code-Classification/master/scripts/install_sdhash.sh | sh

WORKDIR /opt/csd/scripts

# Update clamav database
RUN freshclam

CMD ["/bin/bash", "start_services.sh"]
