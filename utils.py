#####################################################################
# File: utils.py
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
import subprocess as sub

from scripts.elasticdatabase import ElasticDatabase
from scripts.esCfg import EsCfg

TEMP_DIR = "/opt/csd/tmp/csdproject"


# cmd is a list: cmd and options if any
def exec_cmd(cmd):
    p = sub.Popen(cmd, stdout=sub.PIPE, stderr=sub.PIPE)
    output, errors = p.communicate()
    if len(errors.strip()) > 0:
        print cmd, ' >>> ', errors
        return None
    return output
    # todo handle errors


def get_container_base_img(container_id):
    src = os.path.join(os.getcwd(), '../scripts/platform.sh')
    dst = container_id + ':/csdplatform.sh'
    exec_cmd(['docker', 'cp', src, dst])
    base_image = exec_cmd(['docker', 'exec', container_id, '/csdplatform.sh'])
    if not base_image is None:
        base_image = base_image.lower().strip()
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


def check_container(container_id):
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
                print filename + ' match 100%'
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
