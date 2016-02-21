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


class EsDB:
    def __init__(self , configDict):
        self.dstdir = configDict['dstdir']
        self.srcdir = configDict['srcdir']
        self.host = configDict['host']
        self.port = configDict['port']
        self.nodeName = configDict['nodeName']
        self.es = self.get_es_conn(self.host, self.port)

    def get_es_conn(self, host, port):
        print 'connecting to ' + host + ':' + port
        return Elasticsearch([{'host': host, 'port': port}])

    '''
    Saves the all the hashes from dstdir into the Elasticsearch index provided
    :param dstdir:      string, directory where sdbf files are saved in previous step
    :param indexName:   string, index name in elasticsearch, e.g. ubuntu14.04(must be lower case)
    :return:
    '''
    def index_dir(self, path, indexName):
        os.chdir(path)    
        for root, subdirs, files in os.walk(os.getcwd()):
            os.chdir(root)
            #iterate over all the files in path
            for filename in files: 
                #iterate over each line in the file
                with open(filename, "r") as sdhashFile:
                    for line in sdhashFile: 
                        #get file name from sdhash(with suffix if exist)
                        hashName = line.split(':')[3]
                        #set all docType to default
                        docType = 'default'
                        #save item
                        self.put_in_Elastic(indexName, docType, hashName, line) 


    '''
    Saves a single hash into the elasticsearch index provided
    :param indexName:   string, index in elasticsearch e.g. ubuntu14.04(must be lower case)
    :param docType:     string, get from file suffix, if none, use unknown
    :param dirFileName: string, filepath + filename
    :param hashLine:    string, sdhash code for file
    :return:            no return currently
    #TODO check RESTAPI return code and modify return value according to res
    '''
    def put_in_Elastic(self, indexName, docType, dirFileName, hashLine):
        print 'saving item:' + dirFileName
        res = self.es.index(
            index = indexName,
            doc_type = docType,
            id = dirFileName,
            body = {'sdhash':hashLine}
        )
        print res

    '''
    search a file in elasticsearch
    '''
    def get_hash_by_fileName(self, indexName, fileName):
        # Notice: fileName has to be full dir + filename format
        try:
            resDict = self.es.get(index = indexName, id = fileName)
            return resDict
        except:
            print "Can't find match"
            return

    '''
    TODO: pass the customer image name:tag as parameter, gonna use it when saving into judge index
    earch in elasticsearch using filename(full filename with dir), and compute similarity
    :param indexName:   string, reference index in elasticsearch e.g. ubuntu14.04(must be lower case)
    :param fileName:    string, should be filepath + filename that matches the reference
    :return:            no return currently
    '''
    def judge_file_by_filename(self, indexName, fileName):
        #currently indexName should be ubuntu14.04
        fileDict = get_hash_by_fileName(indexName, fileName)
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
        os.system('sdhash -c ./tempCompare/tempref.sdbf ./tempCompare/tempobj.sdbf -t 0 > ./tempCompare/tempRes')
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
            #TODO if use put_in_Elastic, here the body will be {'sdhash': resline}.  Better change the key
            put_in_Elastic(judgeIndex, 'judgeResult', fileName, resline)
            pass
        #clean up
        os.system('rm -r ./tempCompare')

    '''
    Saves the all the hashes from dstdir into the Elasticsearch index provided
    :param dstdir:      string, directory where sdbf files are saved in previous step
    :param refIndexName:   string, index name in elasticsearch, e.g. ubuntu14.04(must be lower case)
    :return:
    '''
    def judge_dir(self, dstdir, refIndexName):
        #TODO check time efficiency
        #commandline 'cd dstdir'
        os.chdir(dstdir)    
        for root, subdirs, files in os.walk(os.getcwd()):
            os.chdir(root)
            for filename in files: 
                #get filepath
                file_path = os.path.join(root, filename) 
                #iterate over each line in the sdbf file
                judgeFileByFileName(indexName, file_path) 

    def delete_index(self, indexName):
        print "U sure you wanna delete index: " + indexName + "?(Y / N)"
        ans = raw_input()
        if ans == 'Y' or ans == 'y':
            if self.es.indices.exists(index=indexName):
                res = self.es.indices.delete(index=indexName)
                print res
            else:
                print 'index does not exist or already removed'


if __name__ == '__main__':
    #try save whatever in dest dir into index: ubuntu14.04
    testEsObj = EsDB(EsCfg)
    # res = testEsObj.index_dir(testEsObj.dstdir, 'ubuntu14.04')
    '''
    res = testEsObj.get_hash_by_fileName(
        'ubuntu14.04', 
        '/home/gladius/Documents/16Spring/CloudComputing/ContainerCodeClassification/scripts/testHash/021/000/021000030'
    )
    '''
    testEsObj.delete_index('ubuntu14.04')
    
    

