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
    print errors
    #print output
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


def calculate_sdhash(imagedir, outputfile):
    print('sdhashing...')
    outputfile = os.path.join(os.getcwd(), 'sdhashed')
    exec_cmd(['sdhash', '-r', imagedir, '-o', outputfile])


def make_dir(path):
    try:
        os.makedirs(path)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise  # raises error
        else:
            pass


def hash_image(imagename):
    imagetar = os.path.join(tmpdir, 'image.tar')
    imagedir = os.path.join(tmpdir, 'image')
    make_dir(TEMP_DIR)
    make_dir(imagetar)
    make_dir(imagedir)

    pull_image(imagename)
    save_image(imagetar, imagename)
    untar_image(imagetar, imagedir)

    calculate_sdhash(imagedir, outputfile)

    #todo cleanup: remove tmp dir



if "__name__" == "__main__":
    # imagename should be in the form image:tag
    # Example test: python csdcheck.py python:2.7.8-slim
    imagename = sys.argv[1]

    hash_image(imagename)
