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
from esCfg import EsCfg

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

    def index_dir(self, path, index):
        """
        Saves hashes from given path into the Elasticsearch
        :param dstdir: string, directory containing sdbf files
        :param index:  string, index name in elasticsearch
                       e.g. ubuntu14.04(must be lower case)
        :return:
        """
        os.chdir(path)
        # if path contains '/' in the end or its root directory(/)
        # TODO: what if path is like "/abc/xyz/////"??
        if path[-1] == '/':
            path = path[:-1]
        for root, subdirs, files in os.walk(os.getcwd()):
            os.chdir(root)
            for filename in files:
                hashName = os.path.join(root, filename)
                hashName = string.replace(hashName, path, "")
                with open(filename, "r") as sdhashFile:
                    line = sdhashFile.read()
                #set all docType to default
                docType = 'default'
                #save item
                self.index_file(index, docType, hashName, line)

    def index_file(self, indexName, docType, dirFileName, hashLine):
        """
        Saves a single hash into the elasticsearch index provided
        :param indexName:   string, index in elasticsearch e.g. ubuntu14.04
        :param docType:     string, get from file suffix
        :param dirFileName: string, filepath + filename
        :param hashLine:    string, sdhash code for file
        :return:            no return currently
        """
        #TODO check REST API return code and return value according to res
        print 'indexing item: ' + dirFileName
        res = self.es.index(
            index = indexName,
            doc_type = docType,
            id = dirFileName,
            body = {'sdhash':hashLine}
        )
        print res

    def search_file(self, index, file):
        """search a file in elasticsearch"""
        # Notice: file name has to be full dir + filename format
        try:
            resDict = self.es.get(index = index, id = file)
            return resDict
        except:
            print "Can't find match"
            return

    def check_similarity(self, indexName, fileName, file_path):
        """
        search in elasticsearch using filename and compute similarity
        :param indexName:  string, reference index in elasticsearch
        :param fileName:   string, should be filename to search
        :param file_path:  string: should be filepath + filename
        :return:           no return currently
        """
        #TODO: pass the customer image name:tag as parameter, 
        #gonna use it when saving into judge index
        #currently indexName should be ubuntu14.04
        fileDict = self.search_file(indexName, fileName)
        refSdhash = fileDict['_source']['sdhash']
        with open("ref_hash", "w") as f:
            f.write(refSdhash)
        file1 = os.path.abspath("ref_hash")
        #TODO: error handling
        resline = self.__exec_cmd(['sdhash', '-c', file1, file_path, '-t 0'])
        score = resline.split('|')[-1]
        if score == "100":
            print fileName + ' match 100%'
        else:
            judgeIndex = 'judgeResult:' + indexName
            # TODO if use index_file, here the body will
            # be {'sdhash': resline}.  Better change the key
            index_file(judgeIndex, 'judgeResult', fileName, resline)
        os.remove("ref_hash")

    def judge_dir(self, path, refIndexName):
        """
        checks similarity for all files in path provided
        filters the suspecious files
        :param path:         string, directory to be scanned
        :param refIndexName: string, reference index in elasticsearch
        :return:
        """
        #TODO check time efficiency
        os.chdir(path)
        # if path contains '/' in the end or its root directory(/)
        # TODO: what if path is like "/abc/xyz/////"??
        if path[-1] == '/':
            path = path[:-1]
        for root, subdirs, files in os.walk(os.getcwd()):
            os.chdir(root)
            for filename in files:
                #get absolute filepath
                file_path = os.path.join(root, filename)
                key = string.replace(file_path, path, "")
                #iterate over each line in the sdbf file
                self.check_similarity(refIndexName, key, file_path)

    def delete_index(self, indexName):
        print "Confirm to delete index: " + indexName + "?(Y / N) "
        ans = raw_input()
        if ans == 'Y' or ans == 'y':
            if self.es.indices.exists(index=indexName):
                res = self.es.indices.delete(index=indexName)
                print res
            else:
                print 'index does not exist or already removed'

    def __exec_cmd(cmd):
        p = sub.Popen(cmd, stdout=sub.PIPE, stderr=sub.PIPE)
        output, errors = p.communicate()
        if len(errors.strip()) > 0:
            print errors
        return output
        # todo handle errors


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
