__author__ = 'rahuls@ccs.neu.edu'

import os
import json
import errno
import string
import logging
import subprocess as sub

from sdhash import gen_hash
from db.elasticsearch.elasticdatabase import ElasticDatabase
from scripts.messagequeue import MessageQueue

from endpoint.endpoint import es_host
from endpoint.endpoint import es_port

logger = logging.getLogger(__name__)

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


def get_base(image):
    path = os.path.join(os.getcwd(), "../scripts")
    mount_path = path + ":/tmp/scripts"
    command = ["docker",
               "run",
               "-v",
               mount_path,
               image,
               "bin/sh",
               "/tmp/scripts/platform.sh"]
    base_image = exec_cmd(command)
    if base_image is not None:
        base_image = base_image.lower().strip()
    return base_image


def untarlayers(imagedir):
    for d in os.listdir(imagedir):
        layerdir = os.path.join(imagedir, d)
        if os.path.isdir(layerdir):
            layertar = os.path.join(layerdir, 'layer.tar')
            exec_cmd(['tar', '-xvf', layertar, '-C', layerdir])
            os.remove(layertar)


def untar(imagetar, imagedir):
    logger.debug('untar...')
    exec_cmd(['tar', '-xvf', imagetar, '-C', imagedir])
    os.remove(imagetar)
    untarlayers(imagedir)


def pull(image):
    logger.debug('docker pull...')
    exec_cmd(['docker', 'pull', image])


def save(imagetar, image):
    logger.debug('docker save...')
    exec_cmd(['docker', 'save', '-o', imagetar, image])


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

    logger.debug('copying layer -- %s', layer)
    layer_path = os.path.join(base_path, layer)
    try:
        for f in os.listdir(layer_path):
            subdir_path = os.path.join(layer_path, f)
            if os.path.isdir(subdir_path):
                exec_cmd(['cp', '-r', subdir_path, dest_dir])
    except BaseException as bex:
        logger.error('exec_cmd error: %s', bex)
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
        parent = get_parent(os.path.join(imagedir, layer_id, 'json'))
        if parent is not None:
            parents.add(parent)

    # The layer that is not in the list of parents must be a leaf
    leaf = None
    for lid in layer_ids:
        if lid not in parents:
            leaf = lid

    logger.debug('all_layers:parent_layers -- %s, : %s', len(layer_ids), len(parents))
    if (len(layer_ids) - len(parents)) != 1 or leaf is None:
        raise  # image should only have one leaf

    return leaf


def get_leaf_and_flatten(imagedir, dest_dir):
    logger.debug('flatenning layers...')
    if not os.path.isdir(dest_dir):
        os.mkdir(dest_dir)

    leaf = get_leaf(imagedir)
    flatten(dest_dir, imagedir, leaf)


def make_dir(path):
    try:
        os.makedirs(path)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise  # raises error
        else:
            pass


#def get_files(image):
#    pass


#def process(image, base, path):
#    pass


def process(image, short_imagename, base, operation, elasticDB):
    print 'Processing image: ', image, '. Operation is: ', operation
    tmpname = string.replace(image, ":", "_")
    imagetar = os.path.join(TEMP_DIR, tmpname, 'image.tar')
    imagedir = os.path.join(TEMP_DIR, tmpname, 'image')
    flat_imgdir = os.path.join(TEMP_DIR, tmpname, 'flat_image')
    dstdir = os.path.join(TEMP_DIR, tmpname, 'hashed_image')

    exec_cmd(['rm', '-rf', TEMP_DIR])
    make_dir(imagedir)
    make_dir(flat_imgdir)
    make_dir(dstdir)

    pull(image)
    save(imagetar, image)
    untar(imagetar, imagedir)

    get_leaf_and_flatten(imagedir, flat_imgdir)

    msg_queue = MessageQueue('localhost', 'dockerqueue', elasticDB)
    process_sdhash(short_imagename, base, flat_imgdir, msg_queue, operation)


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
                sdhash = gen_hash(srcdir, relative_path)
                relative_path = string.replace(relative_path, ':', '_')

                message = {}
                message['image'] = imagename
                message['base_image'] = base_image
                message['relative_path'] = relative_path
                message['operation'] = operation
                message['sdhash'] = sdhash
                message['file_path'] = file_path

                msg_queue.send(json.dumps(message))


def hash_and_index(imagename, operation):
    elasticDB = ElasticDatabase({'host': es_host, 'port': es_port})
    base_image = get_base(imagename)
    print 'Base image is: ', base_image

    # Private registry imagenames would be of
    # format registry-ip:registry-port/image-name:tag
    short_imagename = imagename.split("/")[-1]

    if operation == 'compare' and not elasticDB.check_index_exists(base_image):
        print('Indexing missing base image: ', base_image)
        process(base_image, base_image, base_image, 'store', elasticDB)

    process(imagename, short_imagename, base_image, operation, elasticDB)