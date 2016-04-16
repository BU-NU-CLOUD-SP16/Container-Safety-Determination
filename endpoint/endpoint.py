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
#
# Installing dependencies
# ----------------------------------
# bash$ sudo pip install flask
#
#####################################################################

from flask import Flask
from flask import request
import ConfigParser
import requests
import json
import sys
import os

sys.path.append(os.getcwd() + "/../")
from csdcheck import hash_and_index

global CUR_DIR
CUR_DIR=""

app = Flask(__name__)

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(APP_ROOT, 'settings.ini')

config = ConfigParser.ConfigParser()
config.read(CONFIG_FILE)

username = config.get('registry', 'username')
password = config.get('registry', 'password')
auth = (username, password)


@app.route("/")
def registry_endpoint():
    return "Docker registry endpoint!\n"


@app.route("/notify", methods=['POST'])
def notify():
    #log()
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


def log():
    print request.headers
    print request.args
    print request.data


if __name__ == "__main__":
    CUR_DIR = os.getcwd()
    app.run("0.0.0.0", 9999)
