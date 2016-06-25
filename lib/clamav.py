__author__ = 'rahuls@ccs.neu.edu'

import os
import string
import logging
import subprocess

logger = logging.getLogger(__name__)

# TODO FIX: there should be no requirement of changing file_path (: to _)
def clamscan(file_path):
    ''' Scans the given file with clamAV for detecting vulnerability
    :param file_path: absolute path of file
    :return: result of scanning with clamAV
    '''
    try:
        # if file_path contains ':', replace it with '_'
        file_path = string.replace(file_path, ':', '_')
        if os.path.isfile(file_path):
            clamresult = subprocess.check_output(['clamscan',
                                                  file_path,
                                                  '--no-summary'],
                                                 stderr=subprocess.STDOUT)
            logger.debug("ClamAV scan's result: %s, file: %s" %
                         (clamresult, file_path))
            return clamresult
        else:
            err_msg = "Error: File not found " + file_path
            return err_msg
    except subprocess.CalledProcessError as ex:
        logger.debug("Returncode other than 0 for %s" % file_path)
        return ex.output
