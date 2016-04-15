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


# cmd is a list: cmd and options if any
def exec_cmd(cmd):
    p = sub.Popen(cmd, stdout=sub.PIPE, stderr=sub.PIPE)
    output, errors = p.communicate()
    if len(errors.strip()) > 0:
        print cmd, ' >>> ', errors
        return None
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
        for f in os.listdir(layer_path):
            subdir_path = os.path.join(layer_path, f)
            if os.path.isdir(subdir_path):
                exec_cmd(['sudo', 'cp', '-r', subdir_path, dest_dir])
    except BaseException as bex:
        print 'error has happen: ', bex
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


def gen_sdhash(srcdir, file_path, relative_path):
    full_path = os.path.join(srcdir, relative_path)
    if ':' in relative_path:
        relative_path = string.replace(relative_path, ':', '_')
        tmp_path = os.path.join(srcdir, relative_path)
        exec_cmd(['sudo', 'mv', full_path, tmp_path])
    os.chdir(srcdir)
    return exec_cmd(['sdhash', relative_path])


def get_base_image(cwd, imagename):
    path = os.path.join(cwd, "../scripts")
    print 'libra path ', path
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


# ------------------------------------------------------------------------
# Methods for checking container changes
# ------------------------------------------------------------------------

# 'docker diff' output contains both files and directories.
# parse output to get files only.
# param files: list of file paths
def get_files_only(files):
    files_only = []
    for f in files:
        index = -1 # index to be replaced        
        for idx, filename in enumerate(files_only):
            if (filename[3:] + '/') in f:
                index = idx
                break

        if index > -1:
            files_only[index] = f
        else:
            files_only.append(f)

    return files_only


# Copy files from container to local host
# command format: 'docker cp containerID:/path/to/file  /path/to/local/destination'
def copy_from_container(src, dest):
    exec_cmd(['docker', 'cp', src, dest])


def check_container(container_id, elasticDB, ref_index):
    """
    Check a running container for files that have been changed. If a file
    been changed, determine if it's suspicious by checking if the reference
    dataset contains a file with the same path. If so compare the hash of 
    the file with the reference hash. 
    param container_id: short or full container id
    param elasticDB: instance of ElasticDatabase connected to elasticsearch
               DB containing reference dataset
    param ref_index: index name of reference data set in elasticsearch
    return: Dictionary of suspicious files
    """
    changed_files = {} # filename => similarity score 
    res = exec_cmd(['docker', 'diff', container_id])
    files = res.splitlines()
    files_only = get_files_only(files)

    temp_dir = 'tmpdata'
    if not os.path.exists(temp_dir):
        os.mkdir(temp_dir)

    for s in files_only:
        filename = s[3:] # filename starts at 3
        # check if ref DB contains this file path
        result = elasticDB.search_file(ref_index, filename)

        if result is None:
            changed_files[filename] = -1
        else:
            # found a file with same path
            # compare ref hash with file hash
            ref_sdhash = result['_source']['sdhash']
            features = ref_sdhash.split(":")[10:12]
            if int(features[0]) < 2 and int(features[1]) < 16:
                changed_files[filename] = -2
                continue

            copy_from_container(container_id + ':' + filename, temp_dir)
            basename = os.path.basename(filename)
            file_sdhash = exec_cmd(['sdhash', os.path.join(temp_dir, basename) ])

            with open("file_hash", "w") as f:
                f.write(file_sdhash)
            with open("ref_hash", "w") as f:
                f.write(ref_sdhash)

            file1 = os.path.abspath('file_hash')
            file2 = os.path.abspath('ref_hash')

            # compare file hash with reference hash
            resline = exec_cmd(['sdhash', '-c', file1, file2, '-t','0'])
            resline = resline.strip()
            score = resline.split('|')[-1]
            
            if score == "100":
                print fileName + ' match 100%'
            else:
                changed_files[filename] = score

            os.remove("file_hash")
            os.remove("ref_hash")

    return changed_files


if __name__ == "__main__":
    # TEST IMAGE
    # imagename should be in the form image:tag
    # Example test: python csdcheck.py python:2.7.8-slim
    ##imagename = sys.argv[1]
    ##hash_and_index(imagename)

    # TEST CONTAINER
    container_id = sys.argv[1]
    elasticDB = ElasticDatabase(EsCfg)
    differences = check_container(container_id, elasticDB, 'ubuntu:14.04')
    
    print "SUSPICIOUS FILES"
    space = 36 
    for key in differences:
        print key, ' '*(space-len(key)) , differences[key]
    print 'DONE'
