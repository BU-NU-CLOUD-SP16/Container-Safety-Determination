'''
File requires input:
    a dest dir in esCfg file, we will find out files with suffix sdbf and put every line in that file into elasticsearch
To Retrieve:
    search for filename(with directory) from a index(e.g. ubuntu14.04)
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

 
'''
Filters all the filenames that are not '.sdbf' type.
Takes as input a list of filenames (strings) and returns an updates list with only the sdbf filenames

:param list_of_files:   list, list of files in a directory
:return: updated_list:  list, list of sdbf files filtered
'''
def get_SDBF_files(list_of_files):
    #indexName => Ubuntu14.04   
    return [filename for filename in list_of_files if filename.split('.')[-1] == 'sdbf']

'''
Saves the all the hashes from dstdir into the Elasticsearch index provided
:param dstdir:      string, directory where sdbf files are saved in previous step
:param indexName:   string, index name in elasticsearch, e.g. ubuntu14.04(must be lower case)
:return:
'''
def saveDir(dstdir , indexName):
    #TODO check time efficiency
    i = 0
    #commandline 'cd dstdir'
    os.chdir(dstdir)    
    for root, subdirs, files in os.walk(os.getcwd()):
        os.chdir(root)
        #get a list of all the files with a '.sdbf' suffix
        sdbf_files = files # get_SDBF_files(files)
        #iterate over all the files in the 'dstdir' directory
        for filename in sdbf_files: 
            #get filepath
            file_path = os.path.join(root, filename) 
            # set file destination
            file_dest = file_path.replace(srcdir, dstdir, 1)  
            sdhashFile = open(filename , "r")
            #iterate over each line in the sdbf file
            for line in sdhashFile: 
                print filename
                #get file name from sdhash(with suffix if exist)
                hashName = line.split(':')[3]
                #set all docType to default
                docType = 'default'
                #save item
                put_in_Elastic(indexName, docType , hashName, line) 

'''
Saves a single hash into the elasticsearch index provided
:param indexName:   string, index in elasticsearch e.g. ubuntu14.04(must be lower case)
:param docType:     string, get from file suffix, if none, use unknown
:param dirFileName: string, filepath + filename
:param hashLine:    string, sdhash code for file
:return:            no return currently
#TODO check RESTAPI return code and modify return value according to res
'''
def put_in_Elastic(indexName , docType , dirFileName , hashLine):
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
    # Notice: fileName has to be full dir + filename format
    try:
        resDict = es.get(index = indexName , id = fileName)
        #result in dict
        return resDict
    except:
        "Can't find match"
        return

'''
earch in elasticsearch using filename(full filename with dir), and compute similarity
:param indexName:   string, reference index in elasticsearch e.g. ubuntu14.04(must be lower case)
:param fileName:    string, should be filepath + filename that matches the reference
:return:            no return currently
'''
def judgeFileByFileName(indexName , fileName):
    #currently indexName should be ubuntu14.04
    fileDict = getHashByFileName(indexName , fileName)
    refSdhash = fileDict['_source']['sdhash']
    #save into tempref.sdbf
    #calc current file into tempobj.sdbf
    #compare tempref and tempobj > tempRes
    #read tempRes
    '''
    if score == 100:
        pass
    else:
        #saveIntoJudgeIndex()
        pass
    '''
    #clean up

def deleteIndex(indexName):
    print "U sure you wanna delete index: " + indexName + "?(Y / N)"
    ans = raw_input()
    if ans == 'Y' or ans == 'y':
        print 'deleting: ' + host + ':' + port + '/' + indexName
        res = requests.delete(host + ':' + port + '/' + indexName)
        print res

if __name__ == '__main__':
    #try save whatever in dest dir into index: ubuntu14.04
    res = saveDir(dstdir , 'ubuntu14.04')
    '''
    res = getHashByFileName(
        'ubuntu14.04' , 
        '/home/gladius/Documents/16Spring/CloudComputing/ContainerCodeClassification/scripts/testHash/021/000/021000030'
    )
    '''
    # deleteIndex('ubuntu14.04')
    
    

