## Get suspicious files

http://host:port/get_judge_res/image_name?size=size&offset=offset

e.g. `curl 127.0.0.1:5000/get_judge_res/ubuntu_ref?size=20&offset=40`

## Correct false warning

http://host:port/correct_false_warning/judge_image_dir?file_name=file_name

e.g. `curl 127.0.0.1:5000/correct_false_warning/golden:latest?file_name=/bin/ls`

## Run docker image

http://host:port/docker_run/image_name

e.g. `curl 127.0.0.1:5000/docker_run/`
