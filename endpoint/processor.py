#####################################################################
# File: processor.py
# Author: Jeremy Mwenda <jmwenda@bu.edu>
# Desc: This file processes messages (sdhashes) from rabbitMQ.
#
#####################################################################
import os
import sys

# start from the root directory
sys.path.append("..")

from db.elasticsearch.elasticdatabase import ElasticDatabase
from scripts.messagequeue import MessageQueue
from scripts.esCfg import EsCfg

if __name__ == "__main__":
    elasticDB = ElasticDatabase(EsCfg)
    # TODO: add queuename and host to config
    msg_queue = MessageQueue('localhost', 'dockerqueue', elasticDB)
    msg_queue.start_consuming()