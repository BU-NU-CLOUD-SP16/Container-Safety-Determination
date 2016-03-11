from elasticsearch import Elasticsearch
import json
from flask import * 
app = Flask(__name__)

@app.route('/get_judge_res/<judge_image_dir>')
def get_judge_res(judge_image_dir):
    es = Elasticsearch('10.10.10.15:9200')
    judge_image_dir = 'judgeresult:' + judge_image_dir
    try:
        res_index = es.search(index = judge_image_dir)
    except:
        del(es)
        return 'Error: index do not exist\n'
    res_lst = []
    for item in res_index['hits']['hits']:
        res_lst.append(item['_source']['file'])
    json_res = json.dumps(res_lst)
    del(es)
    return json_res

#is filename should be in md5 or do i need to calculate md5 here?
@app.route('/corrrect_false_warning/<judge_image_dir>/<file_name>')
def correct_false_warning(judge_image_dir, file_name):
    es = Elasticsearch('10.10.10.15:9200')
    judge_image_dir = 'judgeresult:' + judge_image_dir
    try:
        res = es.delete(index = judge_image_dir, doc_type = 'judgeResult', id = file_name)
    except:
        return 'Error: file do not exist\n'
    return res['_shards']

#which machine should run docker image? remotely or locally
#and if word should be a list of arg?
@app.route('/docker_run/<image_name>/<word>') 
def docker_run(image_name, word):
    cmd = ['docker run', image_name, word]
    return os.system('docker run docker/whalesay cowsay ' + word)

if __name__ == '__main__':
    app.run()
