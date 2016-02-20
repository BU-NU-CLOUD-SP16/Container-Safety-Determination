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


#indexName => Ubuntu14.04
def get_SDBF_files(list_of_files):
    '''
    Filters all the filenames that are not '.sdbf' type.
    Takes as input a list of filenames (strings) and returns an updates list with only the sdbf filenames

    :param list_of_files:   list, list of files in a directory
    :return: updated_list:  list, list of sdbf files filtered
    '''
    return [filename for filename in list_of_files if filename.split('.')[-1] == 'sdbf']

#TODO check time efficiency
'''
#TODO: getting root(before /etc) from jeremy script and 
get rid of what ever root before /etc when walking the dir and then save them into elasticsearch
'''
def saveDir(dstdir , indexName):
    '''
    Saves the all the hashes from dstdir into the Elasticsearch index provided
    :param dstdir:      string, directory where sdbf files are saved in previous step
    :param indexName:   string, index name in elasticsearch, e.g. ubuntu14.04(must be lower case)
    :return:
    '''
    i = 0
    os.chdir(dstdir)    #commandline 'cd dstdir'
    for root, subdirs, files in os.walk(os.getcwd()):
        sdbf_files = get_SDBF_files(files) #get a list of all the files with a '.sdbf' suffix
        for filename in sdbf_files: #iterate over all the files in the 'dstdir' directory
            file_path = os.path.join(root, filename) #get filepath
            # SUGGESTION: can't we just do "file_path = root + filename" ? It would be more readable
            # you will get used to it, and it should be "file_path = root + '/' + filename", not a very good style i think
            #TODO, correct directory problem
            file_dest = file_path.replace(srcdir, dstdir, 1)  # set file destination
            sdhashFile = open(filename , "r")
            for line in sdhashFile: #iterate over each line in the sdbf file
                #TODO get cwd and append hashName
                curdir = os.getcwd()
                #get file name from sdhash(with suffix if exist)
                hashName = line.split(':')[3]
                dirFileName = curdir + '/' + hashName
                #split hashName, try to get suffix.  If no suffix, ...
                docType = hashName.split('.')
                if len(docType) > 1:
                    docType = docType[-1]
                else:
                    #since doc type is not that important
                    docType = 'unknown'
                #save item
                put_in_Elastic(indexName, docType , dirFileName, line) #get suffix from filename and set docType

def put_in_Elastic(indexName , docType , dirFileName , hashLine):
    '''
    Saves a single hash into the elasticsearch index provided

    :param indexName:   string, index in elasticsearch e.g. ubuntu14.04(must be lower case)
    :param docType:     string, get from file suffix, if none, use unknown
    :param dirFileName: string, filepath + filename
    :param hashLine:    string, sdhash code for file
    :return:            no return currently
    #TODO check RESTAPI return code and modify return value according to res
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
    # Notice: fileName has to be full dir + filename format
    try:
        resDict = es.get(index = indexName , id = fileName)
        #result in dict
        return resDict
    except:
        "Can't find match"
        return
    

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
    deleteIndex('ubuntu14.04')
    '''
    

