#####################################################################
# File: elasticdatabase.py
# Author: Renqing Gao <gladius@bu.edu>
# Desc:
#
# Input: a dest dir in esCfg file, we will find out files
#        and index them into elasticsearch
#
# To Retrieve: search for filename(with directory) from
#              an index(e.g. ubuntu14.04)
#
#####################################################################

import os
import sys
import json
import string
import requests
import argparse
import hashlib
from esCfg import EsCfg
import subprocess as sub
import time

from elasticsearch import Elasticsearch

class ElasticDatabase:
    def __init__(self, config):
        self.dstdir = config['dstdir']
        self.srcdir = config['srcdir']
        self.host = config['host']
        self.port = config['port']
        self.nodeName = config['nodeName']
        self.es = self.__get_es_conn(self.host, self.port)

    def __get_es_conn(self, host, port):
        #TODO: How should we handle this in case of error???
        return Elasticsearch([{'host': host, 'port': port}])


    def check_container(self, *kwargs):
        pass


if __name__ == '__main__':
    """
    description = "Database providing functionality to store " \
            "sdhashes for files in elasticsearch, ability to " \
            "compare with the stored hashes and predict results"
    parser = argparse.ArgumentParser(description)
    parser.add_argument('--index',
                        action='store_true',
                        default=False,
                        help='index the contents to elasticsearch')

    args = parser.parse_args()
    """

    testEsObj = ElasticDatabase(EsCfg)
    testEsObj.index_file('test1', 'default', '/tests/test1/bin/ls', 'thisisahashNOT', 'safe')
    testEsObj.search_forBasename('test1', '/folder/potato/test2/ls')

'''
    indexName = testEsObj.getIndexName('Ubuntu14.04')
    print indexName
    time.sleep(2)
    indexName2 = testEsObj.getIndexName('Ubuntu14.04')
    print indexName2
    time.sleep(2)
    returnName = testEsObj.getImageName_fromHash('671ee2cf627ddf060f93d3539a7d2c82')
    print 'the name is: ', returnName

    if len(sys.argv) < 2:
        print "Specify operation to perform: --index or --search"
        exit(0)

    command = sys.argv[1]
    if command == "--index":
        path = sys.argv[2]
        index = sys.argv[3]
        testEsObj.index_dir(path, index)
    elif command == "--check":
        path = sys.argv[2]
        index = sys.argv[3]
        testEsObj.judge_dir(path, index)
    else:
        print "Wrong syntax."

'''
