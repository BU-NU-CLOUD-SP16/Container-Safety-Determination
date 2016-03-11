from elasticsearch import Elasticsearch
import json
import hashlib
from flask import * 
app = Flask(__name__)

esport = '10.10.10.15:9200'

@app.route('/get_judge_res/<judge_image_dir>')
def get_judge_res(judge_image_dir):
    es = Elasticsearch(esport)
    judge_image_dir = 'judgeresult:' + judge_image_dir
    search_size = 20
    search_offset = 0
    try:
        if 'offset' in request.args:
            search_offset = int(request.args.get('offset'))
            print search_offset
        res_index = es.search(
            index = judge_image_dir, 
            size = search_size, 
            from_=search_offset
        )
    except:
        del(es)
        return 'Error: index do not exist\n'
    res_lst = []
    for item in res_index['hits']['hits']:
        res_lst.append(item['_source']['file'])
    res_dict = {
        'length' : res_index['hits']['total'],
        'file_list' : res_lst,
        'from_' : search_offset,
        'size' : len(res_index['hits']['hits'])
    }
    json_res = json.dumps(res_dict)
    del(es)
    return json_res

@app.route('/correct_false_warning/<judge_image_dir>')
def correct_false_warning(judge_image_dir):
    es = Elasticsearch(esport)
    if 'file_name' in request.args:
        md5_file_name = hashlib.md5(request.args['file_name']).hexdigest()
        print md5_file_name + ' for ' + request.args['file_name']
    else:
        del(es)
        return 'Error: no file name in request\n'
    judge_image_dir = 'judgeresult:' + judge_image_dir
    try:
        res = es.delete(index = judge_image_dir, doc_type = 'judgeResult', id = md5_file_name)
    except:
        del(es)
        return 'Error: file do not exist\n'
    del(es)
    return json.dumps(res['_shards'])

#which machine should run docker image? remotely or locally
#and if word should be a list of arg?
@app.route('/docker_run/<image_name>') 
def docker_run(image_name):
    es = Elasticsearch(esport)
    #check es again
    judge_image_dir = 'judgeresult:' + image_name
    check_res = es.search(index = judge_image_dir)
    cmd = ['docker run', image_name, word]
    return os.system('docker run docker/whalesay cowsay ' + word)

if __name__ == '__main__':
    app.run()
