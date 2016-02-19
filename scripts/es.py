'''
File requires input:
    a dest dir in esCfg file, we will find out files with suffix sdbf and put every line in that file into elasticsearch
To Retrieve:
    search for filename(with or without directory) from a index(e.g. ubuntu14.04), expected to get every 'bin' from different directory
'''
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

def get_SDBF_files(list_of_files):
    '''
    Filters all the filenames that are not '.sdbf' type.
    Takes as input a list of filenames (strings) and returns an updates list with only the sdbf filenames

    :param list_of_files: list
    :return: updated_list: list
    '''
    return [filename for filename in list_of_files if filename.split('.')[-1] == 'sdbf']

def saveDir(dstdir , indexName):
    '''
    Saves the all the hashes from dstdir into the Elasticsearch index provided
    :param dstdir: string
    :param indexName: string
    :return:
    '''

    os.chdir(dstdir)    #commandline 'cd dstdir'
    for root, subdirs, files in os.walk(dstdir):

        sdbf_files = get_SDBF_files(files) #get a list of all the files with a '.sdbf' suffix

        for filename in sdbf_files: #iterate over all the files in the 'dstdir' directory
            file_path = os.path.join(root, filename) #get filepath
            # SUGGESTION: can't we just do "file_path = root + filename" ? It would be more readable

            file_dest = file_path.replace(srcdir, dstdir, 1)  # set file destination

            sdhashFile = open(filename , "r")

            for line in sdhashFile: #iterate over each line in the sdbf file
            #TODO get pwd and append hashName
                #add dir before name(src dir + hashName, ('/'.join))
                dirFileName = '/'.join(srcdir.split('/').append(hashName))
                #get file name from sdhash(with suffix if exist)
                hashName = line.split(':')[3]
                #split hashName, try to get suffix.  If no suffix, ...
                docType = hashName.split('.')
                if len(docType) > 1:
                    docType = docType[-1]
                else:
                    #TODO how to detect the file type without suffix
                    docType = 'bin'
                put_in_Elastic(indexName, docType , dirFileName, line) #get suffix from filename and set docType

def put_in_Elastic(indexName , docType , dirFileName , hashLine):
    '''
    Saves a single hash into the elasticsearch index provided

    :param indexName:
    :param docType:
    :param dirFileName:
    :param hashLine:
    :return:
    '''
    print 'saving item:' + dirFileName
    res = es.index(
        #ubuntu14.04
        index = indexName,
        #bin
        doc_type = docType,

        #/usr/bin/ls
        id = dirFileName,
        # sdhash string, arg need to be json-like or dice?
        body = {'sdhash':hashLine}
    )
    print res

#search a file in elasticsearch
def getHashByFileName(indexName , fileName):
    #TODO match id instead of body
    res = es.search(index=indexName, body={"query": {"match": {'sdhash':fileName}}})
    #didn't consider multi-match or partial match yet
    print res
    #TODO: this line might fail if no hits?
    # return str(res['hits']['hits'][0]['_source']['sdhash'])
    #return result directly
    return res

def deleteIndex(indexName):
    print "U sure you wanna delete it?(Y / N)"
    ans = raw_input()
    if ans == 'Y' or ans == 'y':
        print 'deleting: ' + host + ':' + port + '/' + indexName
        res = requests.delete(host + ':' + port + '/' + indexName)
        print res

if __name__ == '__main__':
    #try save whatever in dest dir into index: ubuntu14.04
    res = saveDir(dstdir , 'ubuntu14.04')
    #res = getHashByFileName('ubuntu14.04' , '000')
    #deleteIndex('ubuntu14.04')

