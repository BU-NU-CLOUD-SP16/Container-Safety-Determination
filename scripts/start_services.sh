#!/bin/bash

cd ../endpoint
python processor.py &

python endpoint.py
