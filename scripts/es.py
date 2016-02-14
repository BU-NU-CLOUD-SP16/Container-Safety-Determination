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
def saveDir(dstdir , indexName):
    #TODO: filter suffix: .sdbf
    os.chdir(dstdir)
    for root, subdirs, files in os.walk(dstdir):
        for filename in files:
            file_path = os.path.join(root, filename)
            file_dest = file_path.replace(srcdir,dstdir,1)
            sdhashFile = open(filename , "r")
            hashLine = sdhashFile.next()
            print hashLine
            while hashLine:
                print 'got inside'
                hashName = hashLine.split(':')[3]
                #get suffix from filename and set docType
                saveItem(indexName , 'py' , hashName , hashLine)
                hashLine = sdhashFile.next()
                print hashLine

#save one single file into elasticsearch
def saveItem(indexName , docType , hashName , hashLine):
    print 'saving item:' + hashName
    res = es.index(
        #ubuntu14.04
        index = indexName,
        #bin
        doc_type = docType,

        #/usr/bin/ls
        id = hashName,
        # sdhash string, arg need to be json-like or dice?
        body = {'sdhash':hashLine}
    )
    print res

#search a file in elasticsearch
def getHashByFileName(indexName , fileName):
    res = es.search(index=indexName, body={"query": {"match": {'sdhash':fileName}}})
    #didn't consider multi-match or partial match yet
    print res
    #TODO: this line might fail if no hits?
    return str(res['hits']['hits'][0]['_source']['sdhash'])

def deleteIndex(indexName):
    print "U sure you wanna delete it?(Y / N)"
    ans = raw_input()
    if ans == 'Y' or ans == 'y':
        print 'deleting: ' + host + ':' + port + '/' + indexName
        res = requests.delete(host + ':' + port + '/' + indexName)
        print res

if __name__ == '__main__':
    #try save whatever in dest dir into index: ubuntu14.04
    #res = saveDir(dstdir , 'ubuntu14.04')
    #res = getHashByFileName('ubuntu14.04' , '000')
    deleteIndex('ubuntu14.04')

