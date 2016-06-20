__author__ = 'rahuls@ccs.neu.edu'

import os
import sys
import json
import string
import logging
import subprocess as sub

logger = logging.getLogger(__name__)

from db.elasticsearch.elasticdatabase import ElasticDatabase
from scripts.esCfg import EsCfg
from scripts.messagequeue import MessageQueue

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
    if base_image:
        base_image = base_image.lower().strip()
    return base_image


# 'docker diff' output contains both files and directories.
# parse output to get files only.
# param files: list of file paths
def get_files_only(files):
    files_only = []
    for f in files:
        index = -1  # index to be replaced
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


def process(id, base, operation, elasticDB):
    if operation == 'store':
        logger.debug('Processing image: %s. Operation is: %s' %
                     (id, operation))
    else:
        logger.debug('Processing container: %s, Operation is: %s' %
                     (id, operation))

    msg_queue = MessageQueue('localhost', 'dockerqueue', elasticDB)

    changed_files = {}  # filename => similarity score
    res = exec_cmd(['docker', 'diff', id])
    if res is None:
        return json.dumps({'error': 'Error running docker diff.'})

    files = res.splitlines()
    files_only = get_files_only(files)

    temp_dir = 'tmpdata'
    if os.path.exists(temp_dir):
        os.rmdir(temp_dir)
        os.mkdir(temp_dir)
    else:
        os.mkdir(temp_dir)

    for filename in files_only:
        copy_from_container(id + ':' + filename, temp_dir)
        basename = os.path.basename(filename)
        file_path = os.path.join(os.path.abspath(temp_dir), basename)
        file_sdhash = exec_cmd(['sdhash', file_path])
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
            relative_path = filename[1:]
            sdhash = gen_hash(srcdir, file_path, relative_path)
            relative_path = string.replace(relative_path, ':', '_')

            message = {}
            message['image'] = id
            message['base_image'] = base
            message['relative_path'] = relative_path
            message['operation'] = operation
            message['sdhash'] = sdhash
            message['file_path'] = file_path

            msg_queue.send(json.dumps(message))


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
    # TODO: Handle the failure in a better way
    if base_image is None:
        return json.dumps({'error': 'failed to get container base image'})

    elasticDB = ElasticDatabase(EsCfg)
    if not elasticDB.check_index_exists(base_image):
        logger.debug('Indexing missing base image: ', base_image)
        process(base_image, base_image, 'store', elasticDB)

    logger.debug('Reference index is: ', base_image)
    process(container_id, base_image, 'scan', elasticDB)