from elasticsearch import Elasticsearch
import json
import os
import requests
from esCfg import EsCfg

dstdir = EsCfg['dstdir']
srcdir = EsCfg['srcdir']
host = EsCfg['host']
port = EsCfg['port']
nodeName = EsCfg['nodeName']
es = Elasticsearch([{'host': 'localhost', 'port': 9200}])



#put what ever hash in dstdir into elasticsearch
#indexName => Ubuntu14.04
#doc_type
def saveDir(dstdir , indexName , docType):
    for root, subdirs, files in os.walk(dstdir):
        for filename in files:
            file_path = os.path.join(root, filename)
            file_dest = file_path.replace(srcdir,dstdir,1)
            sdhashFile = open(filename , "r")
            hashLine = sdhashFile.next()
            while hashLine:
                hashName = hashLine.split(':')[3]
                saveItem(indexName , hashName , hashLine)

#save one single file into elasticsearch
def saveItem(indexName , docType , hashName , hashLine):
    es.index(
        #ubuntu14.04
        index = indexName, 
        #bin
        doc_type = docTypeName, 
        #/usr/bin/ls
        id = hashName, 
        # sdhash string, arg need to be json-like or dice?
        body = {'sdhash':hashLine}
    )

#search a file in elasticsearch
def getHashByFileName(indexName , fileName):
    res = es.search(index=indexName, body={"query": {"match": {'sdhash':fileName}}})
    #didn't consider multi-match or partial match yet
    return str(res['hits']['hits'][0]['_source']['sdhash'])

if __name__ == '__main__':
	print "still working on it"

