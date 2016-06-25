#####################################################################
# File: processor.py
# Author: Jeremy Mwenda <jmwenda@bu.edu>
# Desc: This file processes messages (sdhashes) from rabbitMQ.
#
#####################################################################
import os
import sys
import ConfigParser

# start from the root directory
sys.path.append("..")

from db.elasticsearch.elasticdatabase import ElasticDatabase
from scripts.messagequeue import MessageQueue

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(APP_ROOT, 'settings.ini')

config = ConfigParser.ConfigParser()
config.read(CONFIG_FILE)

es_host = config.get('elasticsearch', 'host')
es_port = config.get('elasticsearch', 'port')

if __name__ == "__main__":
    elasticDB = ElasticDatabase({'host': es_host, 'port': es_port})
    # TODO: add queuename and host to config
    msg_queue = MessageQueue('localhost', 'dockerqueue', elasticDB)
    msg_queue.start_consuming()