## Prereq

$ pip install -U flask-cors

## Get suspicious files

http://host:port/get_judge_res/image_name?size=size&offset=offset

e.g. `http://127.0.0.1:5000/get_judge_res/ubuntu_ref?size=20&offset=40`

## Correct false warning

http://host:port/correct_false_warning/judge_image_dir?file_name=file_name

e.g. `http://127.0.0.1:5000/correct_false_warning/golden:latest?file_name=/bin/ls`

## Run docker image

http://host:port/docker_run/?image_name=image_name&args=arg1&args=arg2...

e.g. `http://10.10.10.21:5000/docker_run/?image_name=docker/whalesay&args=cowsay&args=boo`
