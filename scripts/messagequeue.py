#####################################################################
# File: csdcheck.py
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
        #print body
        #time.sleep(1)
        parts = body.split('#')
        image = parts[0]
        base_image = parts[1]
        file_path = parts[2]
        operation = parts[3]
        sdhash = parts[4]
        if operation == "store":
            self.es.index_dir(base_image, file_path, sdhash)
        else:
            self.es.judge_dir(base_image, image, file_path, sdhash)

    # continuously process messages
    def start_consuming(self):
        self.channel.basic_consume(self.callback, queue=self.queue, no_ack=True)
        print('Waiting for messages. To exit press CTRL+C')
        self.channel.start_consuming()


    # close connection when done
    def close(self):
        self.conn.close()
