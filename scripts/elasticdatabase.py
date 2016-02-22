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
import json
import requests
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
        for root, subdirs, files in os.walk(os.getcwd()):
            os.chdir(root)
            #iterate over all the files in path
            for filename in files:
                #iterate over each line in the file
                with open(filename, "r") as sdhashFile:
                    for line in sdhashFile:
                        #get file name from sdhash(with suffix if exist)
                        #TODO: what if the filename consists of ':' ???
                        hashName = line.split(':')[3]
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

    def check_similarity(self, indexName, fileName):
        """
        search in elasticsearch using filename(full filename with dir),
        and compute similarity
        :param indexName:  string, reference index in elasticsearch
        :param fileName:   string, should be filepath + filename
        :return:           no return currently
        """
        #TODO: pass the customer image name:tag as parameter, 
        #gonna use it when saving into judge index
        #currently indexName should be ubuntu14.04
        fileDict = search_file(indexName, fileName)
        refSdhash = fileDict['_source']['sdhash']
        os.system('rm -r ./tempCompare')
        os.system('mkdir ./tempCompare')
        os.system('touch ./tempCompare/tempref.sdbf')
        #write searching result to reffile
        temprefFile = open('./tempCompare/tempref.sdbf', 'r+b')
        temprefFile.write(refSdhash)
        temprefFile.close()
        #calc current file into tempobj.sdbf
        #!!!!filename, where can I read this file
        os.system('sdhash ./' + fileName + ' -o ./tempCompare/tempobj')
        #compare tempref and tempobj > tempRes
        os.system('sdhash -c ./tempCompare/tempref.sdbf \
                  ./tempCompare/tempobj.sdbf -t 0 > ./tempCompare/tempRes')
        #read tempRes
        resfile = open('./tempCompare/tempRes')
        resline = resfile.next()
        score = resfile.split('|')[-1]
        #remove \n
        score = score[:-1]
        if score == "100":
            print fileName + ' match 100%'
            pass
        else:
            judgeIndex = 'judgeResult:' + indexName
            # TODO if use index_file, here the body will
            # be {'sdhash': resline}.  Better change the key
            index_file(judgeIndex, 'judgeResult', fileName, resline)
            pass
        #clean up
        os.system('rm -r ./tempCompare')

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
        for root, subdirs, files in os.walk(os.getcwd()):
            os.chdir(root)
            for filename in files:
                #get filepath
                file_path = os.path.join(root, filename)
                #iterate over each line in the sdbf file
                check_similarity(indexName, file_path)

    def delete_index(self, indexName):
        print "Confirm to delete index: " + indexName + "?(Y / N) "
        ans = raw_input()
        if ans == 'Y' or ans == 'y':
            if self.es.indices.exists(index=indexName):
                res = self.es.indices.delete(index=indexName)
                print res
            else:
                print 'index does not exist or already removed'


if __name__ == '__main__':
    testEsObj = ElasticDatabase(EsCfg)
    '''
    res = testEsObj.index_dir(testEsObj.dstdir, 'ubuntu14.04')
    res = testEsObj.search_file(
        'ubuntu14.04',
        '/home/gladius/Documents/16Spring/CloudComputing/ContainerCodeClassification/scripts/testHash/021/000/021000030'
    )
    testEsObj.delete_index('ubuntu14.04')
    '''
