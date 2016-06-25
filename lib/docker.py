#####################################################################
# File: docker.py
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
import logging
import subprocess as sub

from scripts.elasticdatabase import ElasticDatabase
from scripts.messagequeue import MessageQueue

from endpoint.endpoint import es_host
from endpoint.endpoint import es_port


logger = logging.getLogger(__name__)
TEMP_DIR = "/opt/csd/tmp/csdproject"


# For each file in srcdir, calculate sdhash and submit to rabbitmq queue
def process_sdhash(imagename, base_image, srcdir, msg_queue, operation):
    for root, subdirs, files in os.walk(srcdir):
        for filename in files:
            file_path = os.path.join(root, filename)
            file_type = exec_cmd(['file', file_path])

            # only process binary, library files and scripts
            if 'ELF' in file_type or 'executable' in file_type:
                try:
                    size = os.stat(file_path).st_size
                except:
                    continue
                if size < 1024:
                    continue
                # remove srcdir and leading '/' from the path
                relative_path = file_path.replace(srcdir, '', 1)[1:]
                sdhash = gen_sdhash(srcdir, file_path, relative_path)
                relative_path = string.replace(relative_path, ':', '_')

                message = {}
                message['image'] = imagename
                message['base_image'] = base_image
                message['relative_path'] = relative_path
                message['operation'] = operation
                message['sdhash'] = sdhash
                message['file_path'] = file_path

                msg_queue.send(json.dumps(message))


def get_container_base(container_id):
    src = os.path.join(os.getcwd(), '../scripts/platform.sh')
    dst = container_id + ':/csdplatform.sh'
    exec_cmd(['docker', 'cp', src, dst])
    base_image = exec_cmd(['docker', 'exec', container_id, '/csdplatform.sh'])
    if not base_image is None:
        base_image = base_image.lower().strip()
    return base_image


def hash_and_index(imagename, operation):
    elasticDB = ElasticDatabase(EsCfg)
    base_image = get_image_base(imagename)
    print 'Base image is: ', base_image

    # Private registry imagenames would be of
    # format registry-ip:registry-port/image-name:tag
    short_imagename = imagename.split("/")[-1]

    if operation == 'compare' and not elasticDB.check_index_exists(base_image):
        print('Indexing missing base image: ', base_image)
        process_image(base_image, base_image, base_image, 'store', elasticDB)

    process_image(imagename, short_imagename, base_image, operation, elasticDB)


def process_image(imagename, short_imagename, base_image, operation, elasticDB):
    print 'Processing image: ', imagename, '. Operation is: ', operation
    tmpname = string.replace(imagename, ":", "_")
    imagetar = os.path.join(TEMP_DIR, tmpname, 'image.tar')
    imagedir = os.path.join(TEMP_DIR, tmpname, 'image')
    flat_imgdir = os.path.join(TEMP_DIR, tmpname, 'flat_image')
    dstdir = os.path.join(TEMP_DIR, tmpname, 'hashed_image')

    exec_cmd(['rm', '-rf', TEMP_DIR])
    make_dir(imagedir)
    make_dir(flat_imgdir)
    make_dir(dstdir)

    pull(imagename)
    save(imagetar, imagename)
    untar(imagetar, imagedir)

    get_leaf_and_flatten(imagedir, flat_imgdir)

    msg_queue = MessageQueue('localhost', 'dockerqueue', elasticDB)
    process_sdhash(short_imagename, base_image, flat_imgdir, msg_queue, operation)


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
def copy(src, dest):
    exec_cmd(['docker', 'cp', src, dest])


def scan(container_id):
    """
    Check a running container for files that have been changed. If a file
    been changed, determine if it's suspicious by checking if the reference
    dataset contains a file with the same path. If so compare the hash of
    the file with the reference hash.
    param container_id: short or full container id
    return: json string containing suspicious files
    """
    base_image = get_container_base_img(container_id)
    if base_image is None:
        return json.dumps({'error':'failed to get container base image'})

    elasticDB = ElasticDatabase(EsCfg)
    if not elasticDB.check_index_exists(base_image):
        print('Indexing missing base image: ', base_image)
        process_image(base_image, base_image, base_image, 'store', elasticDB)

    print 'Reference index is ', base_image
    changed_files = {} # filename => similarity score
    res = exec_cmd(['docker', 'diff', container_id])
    if res is None:
        return json.dumps({'error':'Error running docker diff.'})

    files = res.splitlines()
    files_only = get_files_only(files)

    temp_dir = 'tmpdata'
    if not os.path.exists(temp_dir):
        os.mkdir(temp_dir)

    for s in files_only:
        filename = s[3:] # filename starts at 3
        # check if ref DB contains this file path
        result = elasticDB.search_file(base_image, filename)

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

    return json.dumps(changed_files)


if __name__ == "__main__":
    # TEST IMAGE
    # imagename should be in the form image:tag
    # Example test: python utils.py python:2.7.8-slim
    ##imagename = sys.argv[1]
    ##hash_and_index(imagename)

    # TEST CONTAINER
    container_id = sys.argv[1]
    os.chdir('endpoint')
    differences = check_container(container_id)

    print 'SUSPICIOUS FILES'
    print differences
    print 'DONE'
