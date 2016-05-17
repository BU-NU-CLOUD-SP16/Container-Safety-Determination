#####################################################################
# File: endpoint.py
# Author: Rahul Sharma <rahuls@ccs.neu.edu>
# Desc: Configures a REST API endpoint listening on port configured.
#       Captures the notifications sent by Docker registry v2,
#       processes them and identifies the newly added or modified
#       image's name and tag. This information is then passed to
#       other module's to download the image and calculate sdhash
#       of all the files within the docker image.
#
# Target platform: Linux
#
# Dependencies
# -----------------
# 1. flask
# 2. flask-cors
#
# Installing dependencies
# ----------------------------------
# bash$ sudo pip install flask && pip install -U flask-cors
#
#####################################################################

from flask import Flask
from flask import request
from flask.ext.cors import CORS
from elasticsearch import Elasticsearch
import logging.config

import ConfigParser
import requests
import hashlib
import json
import sys
import os

sys.path.append(os.getcwd() + "/../")
from utils import hash_and_index, check_container
from scripts.elasticdatabase import ElasticDatabase
from scripts.esCfg import EsCfg

global CUR_DIR
CUR_DIR=""

app = Flask(__name__)
CORS(app)

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(APP_ROOT, 'settings.ini')

config = ConfigParser.ConfigParser()
config.read(CONFIG_FILE)

username = config.get('registry', 'username')
password = config.get('registry', 'password')
auth = (username, password)

logging.config.fileConfig('../logging.conf')
logger = logging.getLogger(__file__)

@app.route("/")
def registry_endpoint():
    return "Docker registry endpoint!\n", 200


@app.route("/notify", methods=['POST'])
def notify():
    #change to CUR_DIR
    os.chdir(CUR_DIR)
    data = json.loads(request.data)

    for event in data["events"]:
        # modifications to images are push events
        if event["action"] == "push":
            repository = event["target"]["repository"]
            url = event["target"]["url"]
            if "manifests" in url:
                # Get the image-blocks in this manifest
                image_blocks = []
                image_manifest = requests.get(url, verify=False, auth=auth)
                for entry in image_manifest.json()["layers"]:
                    image_blocks.append(entry["digest"])

                # Get all tags. Syntax: GET /v2/<name>/tags/list
                temp = url.split("manifests/")
                tags_url = temp[0] + "tags/list"
                tags = requests.get(tags_url, verify=False, auth=auth)

                # Iterate over each tag and get its blocks. If blocks of
                # tag matches with those of the manifest, then this tag
                # is the latest added/modified one. This is just a hack
                # since proper API is not available.
                # Syntax for fetching manifest: GET /v2/<name>/manifests/<tag>
                for tag in tags.json()["tags"]:
                    temp_req = temp[0] + "manifests/" + tag
                    tag_manifest = requests.get(temp_req, verify=False, auth=auth)

                    blocks = []
                    fsLayers = tag_manifest.json()["fsLayers"]
                    for layer in fsLayers:
                        blocks.append(layer["blobSum"])

                    if sorted(image_blocks) == sorted(blocks):
                        print "New image uploaded is: %s | tag: %s" % (repository, tag)
                        host = temp[0].split("/")[2]
                        image = host + "/" + repository + ":" + tag
                        if tag == "golden":
                            hash_and_index(image, "store")
                        else:
                            hash_and_index(image, "compare")
                        break
    return "Done", 200


@app.route('/scan/<container_id>')
def scan_container(container_id):
    result = ''
    try:
        result = check_container(container_id)
    except Exception as e:
        result = json.dumps({'error':'exception: ' + str(e) })
    return result, 200


@app.route('/get_judge_res/<judge_image_dir>')
def get_judge_res(judge_image_dir):
    es = Elasticsearch(EsCfg)
    judge_image_dir = 'judgeresult:' + judge_image_dir
    search_size = 20
    search_offset = 0
    print request.args
    try:
        if 'offset' in request.args:
            search_offset = int(request.args.get('offset'))
        if 'size' in request.args:
            search_size = int(request.args.get('size'))
        res_index = es.search(
            index = judge_image_dir,
            size = search_size,
            from_=search_offset
        )
    except:
        del(es)
        return 'Error: index do not exist\n'
    res_lst = []
    for item in res_index['hits']['hits']:
        res_lst.append(item['_source']['file'])
    res_dict = {
        'total' : res_index['hits']['total'],
        'file_list' : res_lst,
        'from_' : search_offset,
        'size' : len(res_index['hits']['hits'])
    }
    json_res = json.dumps(res_dict)
    del(es)
    return json_res


@app.route('/correct_false_warning/<judge_image_dir>')
def correct_false_warning(judge_image_dir):
    es = Elasticsearch(EsCfg)
    if 'file_name' in request.args:
        md5_file_name = hashlib.md5(request.args['file_name']).hexdigest()
        print md5_file_name + ' for ' + request.args['file_name']
    else:
        del(es)
        return 'Error: no file name in request\n'
    judge_image_dir = 'judgeresult:' + judge_image_dir
    try:
        res = es.delete(index = judge_image_dir, doc_type = 'judgeResult', id = md5_file_name)
    except:
        del(es)
        return 'Error: file do not exist\n'
    del(es)
    return json.dumps(res['_shards'])


#which machine should run docker image? remotely or locally
#and if word should be a list of arg?
@app.route('/docker_run/')
def docker_run():
    es = Elasticsearch(EsCfg)
    #check es again

    #check finished, run docker image
    try:
        image_name = request.args.get('image_name')
    except:
        return 'can not get image_name in request\n'
    arg_lst = request.args.getlist('args')
    cmd = ['docker run', image_name] + arg_lst
    cmd = ' '.join(cmd)
    os.system(cmd)
    return 'done\n'


if __name__ == "__main__":
    CUR_DIR = os.getcwd()
    app.run("0.0.0.0", 9999)
