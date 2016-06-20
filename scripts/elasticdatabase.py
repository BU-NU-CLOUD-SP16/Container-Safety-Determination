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

    def check_container(self, *kwargs):
        pass


if __name__ == '__main__':
    pass