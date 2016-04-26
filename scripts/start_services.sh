#!/bin/bash

/etc/init.d/rabbitmq-server start

cd ../endpoint
python processor.py &

#cp settings_template.ini settings.ini
python endpoint.py
