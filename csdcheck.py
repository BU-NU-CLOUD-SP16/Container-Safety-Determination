#####################################################################
# File: csdcheck.py
# Author: Jeremy Mwenda <jmwenda@bu.edu>
# Desc: This file lists methods which pulls a docker image, untars
#       the content within that image in a specific directory
#       structure and passes it to elasticsearch module for indexing
#       or comparison.
#
# Target platform: Linux
#
# Dependencies
# -----------------
# 1. docker
# 2. sdhash
#
# Installing dependencies
# ----------------------------------
# bash$
#
#####################################################################

import os
import sys
import json
import errno
import string
import subprocess as sub

from scripts.elasticdatabase import ElasticDatabase
from scripts.messagequeue import MessageQueue
from scripts.esCfg import EsCfg

TEMP_DIR = "/tmp/csdproject"


# cmd is a list: cmd and options if any
def exec_cmd(cmd):
    p = sub.Popen(cmd, stdout=sub.PIPE, stderr=sub.PIPE)
    output, errors = p.communicate()
    if len(errors.strip()) > 0:
        print cmd, ' >>> ', errors
    return output
    # todo handle errors


def untarlayers(imagedir):
    for d in os.listdir(imagedir):
        layerdir = os.path.join(imagedir, d)
        if os.path.isdir(layerdir):
            layertar = os.path.join(layerdir, 'layer.tar')
            exec_cmd(['sudo', 'tar', '-xvf', layertar, '-C', layerdir])
            os.remove(layertar)


def untar_image(imagetar, imagedir):
    print('untar...')
    exec_cmd(['tar', '-xvf', imagetar, '-C', imagedir])
    os.remove(imagetar)
    untarlayers(imagedir)


def pull_image(imagename):
    print('docker pull...')
    exec_cmd(['docker', 'pull', imagename])


def save_image(imagetar, imagename):
    print('docker save...')
    exec_cmd(['docker', 'save', '-o', imagetar, imagename])


# Read a layer's json file and get ID of parent layer
def get_parent(json_file):
    with open(json_file) as data_file:
        data = json.load(data_file)
    if 'parent' in data:
        return data['parent']
    return None


"""Combine all image layers into a single layer.
If a file exists in multiple layer, only the latest file is kept.
:param dest_dir: full-path output directory.
:param base_path: full-path to directory containing layers
:param layer: directory basename of layer to be parsed
"""
def flatten(dest_dir, base_path, layer):
    json_file = os.path.join(base_path, layer, 'json')
    with open(json_file) as data_file:
        data = json.load(data_file)
    if 'parent' in data:
        parent = data['parent']
        flatten(dest_dir, base_path, parent) #recursive

    print('copying layer -- ', layer)
    layer_path = os.path.join(base_path, layer)
    try:
        os.system('sudo cp -r ' + layer_path + '/* ' + dest_dir)
    except:
        return


# Determine leaf layer by checking the json file of each layer..
def get_leaf(imagedir):
    layer_ids = set()
    for f in os.listdir(imagedir):
        # The name of each directory is a layer ID
        if os.path.isdir(os.path.join(imagedir, f)):
            layer_ids.add(f)

    # Layers that are parents
    parents = set()
    for layer_id in layer_ids:
        parent = get_parent(os.path.join(imagedir,layer_id,'json'))
        if parent is not None:
            parents.add(parent)

    # The layer that is not in the list of parents must be a leaf
    leaf = None
    for lid in layer_ids:
        if lid not in parents:
            leaf = lid

    print('all_layers:parent_layers -- ', len(layer_ids), ':', len(parents))
    if (len(layer_ids) - len(parents)) != 1 or leaf is None:
        raise # image should only have one leaf

    return leaf


def get_leaf_and_flatten(imagedir,dest_dir):
    print('flatenning layers...')
    if not os.path.isdir(dest_dir):
        os.mkdir(flatdir)

    leaf = get_leaf(imagedir)
    flatten(dest_dir, imagedir, leaf)
    dev_dir = os.path.join(dest_dir, "dev")
    exec_cmd(['sudo', 'rm', '-rf', dev_dir])


def make_dir(path):
    try:
        os.makedirs(path)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise  # raises error
        else:
            pass


# For each file in srcdir, calculate sdhash and write to file in dstdir
# Example: sdhash for file srcdir/usr/local/bin/prog1 will be written to dstdir/usr/local/bin/prog1
def process_sdhash(imagename, base_image, srcdir, msg_queue, operation):
    for root, subdirs, files in os.walk(srcdir):
        for filename in files:
            file_path = os.path.join(root, filename)
            file_type = exec_cmd(['file',file_path])
            
            # only process binary, library files and scripts
            if 'ELF' in file_type or 'executable' in file_type:
                try:
                    size = os.stat(file_path).st_size
                except:
                    continue
                if size < 1024:
                    continue
                relative_path = file_path.replace(srcdir, '', 1)[1:] # 1: to remove '/'
                sdhash = gen_sdhash(srcdir, file_path, relative_path)
                image = imagename.split("/")[1]
                relative_path = string.replace(relative_path, ':', '_')

                message = {}
                message['image'] = image
                message['base_image'] = base_image
                message['relative_path'] = relative_path
                message['operation'] = operation
                message['sdhash'] = sdhash

                msg_queue.send(json.dumps(message))


def gen_sdhash(srcdir, file_path, relative_path):
    full_path = os.path.join(srcdir, relative_path)
    if ':' in relative_path:
        relative_path = string.replace(relative_path, ':', '_')
        tmp_path = os.path.join(srcdir, relative_path)
        exec_cmd(['sudo', 'mv', full_path, tmp_path])
    os.chdir(srcdir)
    return exec_cmd(['sdhash', relative_path])


def get_base_image(imagename):
    path = os.path.join(os.getcwd(), "../scripts")
    mount_path = path + ":/tmp/scripts"
    command = ["docker",
               "run",
               "-v",
               mount_path,
               imagename,
               "bin/sh",
               "/tmp/scripts/platform.sh"]
    base_image = exec_cmd(command).lower()
    base_image = base_image.strip()
    return base_image


def hash_and_index(imagename, operation):
    tmpname = string.replace(imagename, ":", "_")
    imagetar = os.path.join(TEMP_DIR, tmpname, 'image.tar')
    imagedir = os.path.join(TEMP_DIR, tmpname, 'image')
    flat_imgdir = os.path.join(TEMP_DIR, tmpname, 'flat_image')
    dstdir = os.path.join(TEMP_DIR, tmpname, 'hashed_image')
    #make_dir(TEMP_DIR)
    exec_cmd(['sudo', 'rm', '-rf', TEMP_DIR])
    make_dir(imagedir)
    make_dir(flat_imgdir)
    make_dir(dstdir)
    make_dir("/tmp/files") # for debugging purpose, will remove it

    #print imagename
    pull_image(imagename)
    save_image(imagetar, imagename)
    untar_image(imagetar, imagedir)

    get_leaf_and_flatten(imagedir, flat_imgdir)

    elasticDB = ElasticDatabase(EsCfg)
    base_image = get_base_image(imagename)
    print 'Base image is: ', base_image
    print 'Operation is: ', operation
    msg_queue = MessageQueue('localhost', 'dockerqueue', elasticDB)
    process_sdhash(imagename, base_image, flat_imgdir, msg_queue, operation)

    # Since its for private registry images, imagename would be
    # of format registry-ip:registry-port/image-name:tag
    #image = imagename.split("/")[1]
    #print "Index data"
    #elasticDB.index_dir(dstdir, image)
    #TODO: image = find_image_name(image)
    ## elasticDB.judge_dir(dstdir, image)
    #todo cleanup: remove tmp dir


if __name__ == "__main__":
    # imagename should be in the form image:tag
    # Example test: python csdcheck.py python:2.7.8-slim
    imagename = sys.argv[1]

    hash_and_index(imagename)
