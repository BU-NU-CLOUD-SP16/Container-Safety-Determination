#####################################################################
# File: processor.py
# Author: Jeremy Mwenda <jmwenda@bu.edu>
# Desc: This file processes messages (sdhashes) from rabbitMQ.
#
#######
import os
import sys
import time
import Queue
import threading

sys.path.append(os.getcwd() + "/../")
from scripts.elasticdatabase import ElasticDatabase
from scripts.messagequeue import MessageQueue
from scripts.esCfg import EsCfg
from utils import *

FILE_QUEUE = Queue.Queue()
SDHASH_QUEUE = Queue.Queue()

class FileProcessor (threading.Thread):
    def __init__(self, thread_Id):
        self.thread_Id = thread_Id
        thread = threading.Thread(target=self.run, args=())
        thread.daemon = True         # Daemonize thread
        thread.start()               # Start the execution

    def run(self):
        print "Starting thread FileProcessor ", self.thread_Id
        while True:
            item = FILE_QUEUE.get()
            #print 'processing file ...', self.thread_Id
            process_file(item)
            FILE_QUEUE.task_done()
        print "Exiting FileProcessor thread"

class IndexOrLookup (threading.Thread):
    def __init__(self, thread_Id):
        self.thread_Id = thread_Id
        self.elasticDB = ElasticDatabase(EsCfg)
        thread = threading.Thread(target=self.run, args=())
        thread.daemon = True         # Daemonize thread
        thread.start()               # Start the execution

    def run(self):
        print "Starting thread IndexOrLookup ", self.thread_Id
        ct = 0
        while True:
            ct = ct + 1
            message = SDHASH_QUEUE.get()
            data = json.loads(message)

            image = data['image']
            base_image = data['base_image']
            file_path = data['relative_path']
            operation = data['operation']
            sdhash = data['sdhash']
            if ct % 100 == 0:
                print self.thread_Id, ' ', ct

            if operation == "store":
                self.elasticDB.index_dir(base_image, file_path, sdhash)
            else:
                self.elasticDB.judge_dir(base_image, image, file_path, sdhash)
            SDHASH_QUEUE.task_done()
        print "Exiting thread IndexOrLookup"

def process_image(imagename, operation):
    TEMP_DIR = '/tmp/csdproject' + str(time.time()).replace('.', '', 1)
    print('TEMP_DIR is ', TEMP_DIR)
    tmpname = string.replace(imagename, ":", "_")
    imagetar = os.path.join(TEMP_DIR, tmpname, 'image.tar')
    imagedir = os.path.join(TEMP_DIR, tmpname, 'image')
    flat_imgdir = os.path.join(TEMP_DIR, tmpname, 'flat_image')
    dstdir = os.path.join(TEMP_DIR, tmpname, 'hashed_image')

    exec_cmd(['sudo', 'rm', '-rf', TEMP_DIR])
    make_dir(imagedir)
    make_dir(flat_imgdir)
    make_dir(dstdir)
    make_dir("/tmp/files") # for debugging purpose, will remove it

    pull_image(imagename)
    save_image(imagetar, imagename)
    untar_image(imagetar, imagedir)

    get_leaf_and_flatten(imagedir, flat_imgdir)

    base_image = get_base_image(CUR_DIR, imagename)
    print 'Base image is: ', base_image
    print 'Operation is: ', operation

    message = {}
    message['image'] = imagename
    message['base_image'] = base_image
    message['operation'] = operation
    message['base_dir'] = flat_imgdir

    for root, subdirs, files in os.walk(flat_imgdir):
        for filename in files:
            file_path = os.path.join(root, filename)
            message['file_path'] = file_path
            FILE_QUEUE.put(json.dumps(message))

    print 'process_image end'


def process_file(item):
    data = json.loads(item)
    imagename = data['image']
    base_image = data['base_image']
    operation = data['operation']
    base_dir  = data['base_dir']
    file_path = data['file_path']

    # only process binary, library files and scripts
    file_type = exec_cmd(['file',file_path])
    if 'ELF' in file_type or 'executable' in file_type:
        try:
            size = os.stat(file_path).st_size
        except:
            return
        if size < 1024:
            return
        relative_path = file_path.replace(base_dir, '', 1)[1:] # 1: to remove '/'
        sdhash = gen_sdhash(base_dir, file_path, relative_path)

        # Since its for private registry images, imagename would be
        # of format registry-ip:registry-port/image-name:tag
        image = imagename.split("/")[1]
        relative_path = string.replace(relative_path, ':', '_')

        message = {}
        message['image'] = image
        message['base_image'] = base_image
        message['relative_path'] = relative_path
        message['operation'] = operation
        message['sdhash'] = sdhash

        SDHASH_QUEUE.put(json.dumps(message))

def rmq_callback(ch, method, properties, body):
    print "rmq_callback"
    image = body
    print 'processing image ', image
    tag = image.split(':')[-1]
    operation = 'compare'
    if tag == "golden":
        operation = 'store'

    process_image(image, operation)
    

if __name__ == "__main__":
    global CUR_DIR
    CUR_DIR = os.getcwd()
    proc_thread1 = FileProcessor('Procthread1')
    proc_thread2 = FileProcessor('Procthread2')

    index_thread1 = IndexOrLookup('Idxthread1')
    index_thread2 = IndexOrLookup('Idxthread2')

    elasticDB = ElasticDatabase(EsCfg)
    # TODO: add queuename and host to config
    msg_queue = MessageQueue('localhost', 'dockerqueue', elasticDB)
    try:
        msg_queue.start_consuming(rmq_callback)
    except KeyboardInterrupt:
        msg_queue.close()

    print "Done"
