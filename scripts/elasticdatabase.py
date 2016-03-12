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

    def index_dir(self, index_name, file_name, file_sdhash):
        """
        Saves hashes from given path into the Elasticsearch
        :param dstdir: string, directory containing sdbf files
        :param index:  string, index name in elasticsearch
                       e.g. ubuntu14.04(must be lower case)
        :return:
        """
        # set all docType to default
        docType = 'default'
        # save item
        self.index_file(index_name, docType, file_name, file_sdhash)

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
        id = hashlib.md5(dirFileName).hexdigest()
        res = self.es.index(
            index = indexName,
            doc_type = docType,
            id = id,
            body = {'file': dirFileName, 'sdhash': hashLine}
        )
        print res

    def search_file(self, index, file):
        """search a file in elasticsearch"""
        # Notice: file name has to be full dir + filename format
        try:
            id = hashlib.md5(file).hexdigest()
            resDict = self.es.get(index = index, id = id)
            return resDict
        except:
            print "Can't find match"
            return


    def getIndexName(self, imageName):
        '''Computes and returns the index name for the image to be stored.

        In order to control for index-name errors with ES (with problematic characters),
        we're storing each image into the index of its hash.

        e.g. 'Ubuntu14.04' to be stored in index named '52250eb3f1ccec5a687c4a4d14775e9d'
        The function hashes the imageName and returns the hash.
        For future retrieval of the name, the function stores the imagehash:imagename in
        the index 'ImageHashes'

        :param imageName: string - name of the image we're passing e.g. "ubuntu_14.04"
        :return: id - string - name of the index to be stored in
        '''
        index = 'imageHashes'
        searchIndex = self.search_file(index, imageName)
        print searchIndex

        if searchIndex != None:
            return searchIndex['id']
        else:
            id = hashlib.md5(imageName).hexdigest()
            res = self.es.index(
                index = 'imageHashes',
                doc_type = 'image file',
                id = id,
                body = {'image': imageName}
            )
            return id

    def getImageName_fromHash(self, hash):
        '''
        Retrieves the original image name from a given hash. 
        E.g. If you input '52250eb3f1ccec5a687c4a4d14775e9d' it returns 'ubuntu14.04'
        
        :param hash: string - the hash of the imagename to be retrieved
        :return: imageName: string - the original name of the image
        '''
        index = 'ImageHashes'

        try:
            foundImage = self.es.get(index = index, id = hash)
            imageName = foundImage['body']['image']
            return imageName
        except:
            print "Can't find match"
            return
        
    def check_similarity(self, ref_index, image_name, fileName, file_sdhash):
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
        fileDict = self.search_file(ref_index, fileName)
        if fileDict == None:
            print "skip file as its not present"
            return
        ref_sdhash = fileDict['_source']['sdhash']
        features = refSdhash.split(":")[10:12]
        if int(features[0]) < 2 and int(features[1]) < 16:
            print "skipping since only one component with < 16 features"
            return
        with open("file_hash", "w") as f:
            f.write(file_sdhash)
        with open("ref_hash", "w") as f:
            f.write(ref_sdhash)
        file1 = os.path.abspath('file_hash')
        file2 = os.path.abspath('ref_hash')
        #TODO: error handling
        resline = self.__exec_cmd(['sdhash', '-c', file1, file2, '-t','0'])
        resline = resline.strip()
        score = resline.split('|')[-1]
        if score == "100":
            print fileName + ' match 100%'
        else:
            # Copy suspicious files just for debugging purpose
            # test_path = file_path
            # test_path = string.replace(test_path, "hashed_image", "flat_image")
            # self.__exec_cmd(['cp', test_path, '/tmp/files'])

            judgeIndex = 'judgeresult:' + image_name
            # TODO if use index_file, here the body will
            # be {'sdhash': resline}.  Better change the key
            self.index_file(judgeIndex, 'judgeResult', fileName, resline)
        os.remove("file_hash")
        os.remove("ref_hash")


    def judge_dir(self, refIndexName, image_name, file_name, file_sdhash):
        """
        checks similarity for all files in path provided
        filters the suspecious files
        :param path:         string, directory to be scanned
        :param refIndexName: string, reference index in elasticsearch
        :return:
        """
        #TODO check time efficiency
        self.check_similarity(refIndexName, image_name, file_name, file_sdhash)

    def delete_index(self, indexName):
        print "Confirm to delete index: " + indexName + "?(Y / N) "
        ans = raw_input()
        if ans == 'Y' or ans == 'y':
            if self.es.indices.exists(index=indexName):
                res = self.es.indices.delete(index=indexName)
                print res
            else:
                print 'index does not exist or already removed'

    def __exec_cmd(self, cmd):
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

