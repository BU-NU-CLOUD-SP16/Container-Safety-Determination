__author__ = 'rahuls@ccs.neu.edu'

import subprocess as sub

import os
import logging
import string

logger = logging.getLogger(__name__)


def exec_cmd(cmd):
    try:
        p = sub.Popen(cmd, stdout=sub.PIPE, stderr=sub.PIPE)
        output, errors = p.communicate()
        if p.returncode != 0:
            print errors
        return output
    except:
        print "Error occurred."


def compare_files(file1, file2):
    try:
        score = exec_cmd(['sdhash', '-c', file1, file2, '-t', '0'])
        score = score.strip()
        return score.split('|')[-1]
    except:
        logger.debug("Sdhash comparison failed for %s, %s.", file1, file2)
        return -1


def compare_hashes(hash1, hash2):
    try:
        with open("file_hash", "w") as f:
            f.write(hash1)
        with open("ref_hash", "w") as f:
            f.write(hash2)
        file1 = os.path.abspath('file_hash')
        file2 = os.path.abspath('ref_hash')
        result = compare_files(file1, file2)
        os.remove(file1)
        os.remove(file2)
        return result
    except:
        logger.debug("comparing sdhashes failed.")
        return -1


def valid_hash(hash):
    # https://github.com/sdhash/sdhash/issues/5
    components, features = hash.split(":")[10:12]
    if int(components) < 2 and int(features) < 16:
        return False
    return True


def gen_hash(srcdir, relative_path):
    full_path = os.path.join(srcdir, relative_path)
    if ':' in relative_path:
        relative_path = string.replace(relative_path, ':', '_')
        tmp_path = os.path.join(srcdir, relative_path)
        exec_cmd(['mv', full_path, tmp_path])
    os.chdir(srcdir)
    return exec_cmd(['sdhash', relative_path])


