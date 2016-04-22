# Get base image
FROM ubuntu:15.04

# Install the required packages
RUN apt-get update && apt-get -y install python-pip rabbitmq-server git wget && pip install Flask && pip install elasticsearch && pip install pika

# Install docker
RUN wget -qO- https://get.docker.com/ | sh

# Package the code
RUN git clone https://github.com/BU-NU-CLOUD-SP16/Container-Code-Classification /usr/local/ccs
#ADD Container-Code-Classification  /usr/local/ccs/

# Port number to be exposed by Container
#EXPOSE 9999

WORKDIR /usr/local/ccs/scripts

RUN /usr/local/ccs/scripts/install_sdhash.sh

CMD ["/bin/bash", "start_services.sh"]
