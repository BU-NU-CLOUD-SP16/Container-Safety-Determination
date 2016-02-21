#####################################################################
# File: csdcheck.py
# Author: Jeremy Mwenda <jmwenda@bu.edu>
# Desc:
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
import errno
import shutil
import subprocess as sub

TEMP_DIR = "/tmp/csdproject"

# cmd is a list: cmd and options if any
def exec_cmd(cmd):
    p = sub.Popen(cmd, stdout=sub.PIPE, stderr=sub.PIPE)
    output, errors = p.communicate()
    if len(errors.strip()) > 0:
        print errors
    return output
    # todo handle errors


def untarlayers(imagedir):
    for d in os.listdir(imagedir):
        layerdir = os.path.join(imagedir, d)
        if os.path.isdir(layerdir):
            layertar = os.path.join(layerdir, 'layer.tar')
            exec_cmd(['tar', '-xvf', layertar, '-C', layerdir])
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
def calculate_sdhash(srcdir, dstdir):
    for root, subdirs, files in os.walk(srcdir):
        for subdir in subdirs:
            sub_path = os.path.join(root, subdir)
            sub_dest = sub_path.replace(srcdir, dstdir, 1)
            if not os.path.exists(sub_dest):
                os.makedirs(os.path.join(sub_dest))

        for filename in files:
            file_path = os.path.join(root, filename)
            file_dest = file_path.replace(srcdir, dstdir, 1)

        gen_sdhash(file_path, file_dest, srcdir)


def gen_sdhash(file_path, file_dest, srcdir):
    os.chdir(srcdir)
    path = file_path.split(srcdir)
    res = exec_cmd(['sdhash', path[1][1:]])
    with open(file_dest, 'w') as f:
        f.write(res)


def hash_and_index(imagename):
    imagetar = os.path.join(TEMP_DIR, 'image.tar')
    imagedir = os.path.join(TEMP_DIR, 'image')
    dstdir = os.path.join(TEMP_DIR, 'hashed_image')
    make_dir(TEMP_DIR)
    make_dir(imagedir)
    make_dir(dstdir)

    print imagename
    pull_image(imagename)
    save_image(imagetar, imagename)
    untar_image(imagetar, imagedir)

    calculate_sdhash(imagedir, dstdir)

    #todo cleanup: remove tmp dir


if "__name__" == "__main__":
    # imagename should be in the form image:tag
    # Example test: python csdcheck.py python:2.7.8-slim
    imagename = sys.argv[1]

    hash_and_index(imagename)
