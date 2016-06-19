__author__ = 'rahuls@ccs.neu.edu'

from db.database import BaseDatabase
from elasticsearch import Elasticsearch
import logging
import hashlib

logger = logging.getLogger(__name__)


class ElasticDatabase(BaseDatabase):

    def __init__(self, config):
        self.host = config['host']
        self.port = config['port']
        self.nodeName = config['nodeName']
        self.es = Elasticsearch([{'host': self.host, 'port': self.port}])

    def index(self, **kwargs):
        """Indexes file in elasticsearch.
        :param index:    string, index in elasticsearch e.g. ubuntu14.04
        :param filename: string, (filepath + filename)
        :param body:     message to be indexed in elasticsearch
        :return:         no return currently
        """
        #TODO: return REST API return code
        index = kwargs.get("index")
        filename = kwargs.get("filename")
        body = kwargs.get("body")
        logger.debug("Indexing item: %s", filename)

        # id is md5 hash of filename
        id = hashlib.md5(filename).hexdigest()
        docType = 'default'
        res = self.es.index(index=index, doc_type=docType, id=id, body=body)
        print res

    def search(self, **kwargs):
        """Searches a file in Elasticsearch. Returns if object is found
        Note: filename has to be full dir + filename format
        """
        logger.debug("searching for dir path...")
        index = kwargs.get("index")
        filename = kwargs.get("filename")
        try:
            id = hashlib.md5(filename).hexdigest()
            resDict = self.es.get(index=index, id=id)
            return resDict
        except:
            logger.debug("Can't find file match for %s", filename)
            return None

    def search_basename(self, **kwargs):
        """Searches for a file's basename in the database.
        param: file_path, file
        param: index, elasticsearch index-name
        """
        print 'searching for basename...'
        file_path = kwargs.get("file_path")
        index = kwargs.get("index")
        base = file_path.split('/')[-1]  # get basename out of the path
        try:
            resDict = self.es.search(index=index, body={"query": {"match": {'basename': base}}})
            print 'Object Found: ', resDict
            return resDict
        except:
            print "Can't find basename match"
            return

    def delete_index(self, index):
        print "Confirm to delete index: " + index + "?(Y to confirm): "
        ans = raw_input()
        if ans.lower() == 'y':
            if self.es.indices.exists(index=index):
                res = self.es.indices.delete(index=index)
                print res
            else:
                print 'Index does not exist or already removed'
        else:
            print "You selected not to delete the index"

    def get_index_name(self, image_name):
        """Computes and returns the index name for the image to be stored.
        For controlling index-name errors in ES (with problematic characters),
        we're storing each image into the index of its hash.
        e.g. 'Ubuntu14.04' will be stored in index named '52250eb3f1c......'

        This function hashes the imageName and returns the hash.
        For future retrieval of the name, the function stores the
        imagehash:imagename in the index 'ImageHashes'

        :param image_name: string - name of the image e.g. "ubuntu_14.04"
        :return: id - string - name of the index
        """
        index = 'imagehashes'
        id = hashlib.md5(image_name).hexdigest()
        res = self.search(index=index, filename=id)

        if res:
            return res['_id']
        else:
            # TODO: try/except here for error-handling
            res = self.es.index(index='imagehashes',
                                doc_type='image file',
                                id=id,
                                body={'image': image_name})
            return id

    def hash_to_name(self, hash):
        """Retrieves the original image name from a given hash.
        E.g. If you input '52250eb3f1.....' it returns 'ubuntu14.04'

        :param hash: string - the hash of the imagename to be retrieved
        :return: imageName: string - the original name of the image
        """
        index = 'imagehashes'
        try:
            # TODO: error handling
            res = self.es.get(index=index, id=hash)
            return res['_source']['image']
        except:
            print "Can't find image match"
            return None

    def check_index_exists(self, index_name):
        return self.es.indices.exists(index=index_name)