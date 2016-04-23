#####################################################################
# File: messagequeue.py
# Author: Jeremy Mwenda <jmwenda@bu.edu>
# Desc: Class MessageQueue is used for sending and receiving messages from RMQ.
# An instance of this class should only be used for either sending or receiving, not both.
# TODO: add hostname and queue name to config file
# TODO: handle RMQ exceptions
#
# Dependencies:
# rabbitmq-server
# pika -- pip install pika 
#
#####################################################################

import pika
import json
import time # remove

class MessageQueue:
    def __init__(self, host, queue, elasticDB):
        self.host = host
        self.queue = queue
        self.conn = self.__get_connection(self.host)
        self.channel = self.conn.channel()
        self.channel.queue_declare(queue=queue) # create/ensure queue exists
        self.es = elasticDB

    def __get_connection(self, host):
        return pika.BlockingConnection(pika.ConnectionParameters(host))

    # send message using default exchange 
    def send(self, message):
        self.channel.basic_publish(exchange='', routing_key=self.queue, body=message)
        #print 'Done sending: ', message


    # declare a callback to process received message
    def callback(self, ch, method, properties, body):
        data = json.loads(body)
        image = data['image']
        base_image = data['base_image']
        file_path = data['relative_path']
        operation = data['operation']
        sdhash = data['sdhash']
        file = data['file_path']

        if operation == "store":
            basename = file_path.split('/')[-1]
            body = {'file': file_path,
                    'sdhash': sdhash,
                    'basename': basename}
            self.es.index_file(base_image, file_path, body)
        else:
            self.es.check_similarity(base_image, image, file, file_path, sdhash)

    # continuously process messages
    def start_consuming(self):
        self.channel.basic_consume(self.callback, queue=self.queue, no_ack=True)
        print('Waiting for messages. To exit press CTRL+C')
        self.channel.start_consuming()


    # close connection when done
    def close(self):
        self.conn.close()
