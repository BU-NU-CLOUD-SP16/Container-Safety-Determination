__author__ = 'rahuls@ccs.neu.edu'

import os
import string
import logging
import subprocess as sub

logger = logging.getLogger(__name__)

# TODO FIX: there should be no requirement of changing file_path (: to _)
def scan(file_path):
    try:
        file_path = string.replace(file_path, ':', '_')
        if os.path.isfile(file_path):
            clamresult = sub.check_output(['clamscan',
                                          file_path,
                                          '--no-summary'],
                                          stderr=sub.STDOUT)
            logger.debug("clamscan's result: %s, file: %s", clamresult, file_path)
            return clamresult
        else:
            err_msg = "Error: File not found " + file_path
            return err_msg
    except sub.CalledProcessError as ex:
        logger.debug("Returncode other than 0 for %s", file_path)
        return ex.output
