from elasticsearch import Elasticsearch
import json
import os
import hashlib
from flask import * 
from flask.ext.cors import cors

app = Flask(__name__)
CORS(app)

esport = '10.10.10.15:9200'

@app.route('/get_judge_res/<judge_image_dir>')
def get_judge_res(judge_image_dir):
    es = Elasticsearch(esport)
    judge_image_dir = 'judgeresult:' + judge_image_dir
    search_size = 20
    search_offset = 0
    print request.args
    try:
        if 'offset' in request.args:
            search_offset = int(request.args.get('offset'))
        if 'size' in request.args:
            search_size = int(request.args.get('size'))
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
        'total' : res_index['hits']['total'],
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
@app.route('/docker_run/') 
def docker_run():
    es = Elasticsearch(esport)
    #check es again

    #check finished, run docker image
    try:
        image_name = request.args.get('image_name')
    except:
        return 'can not get image_name in request\n'
    arg_lst = request.args.getlist('args')
    cmd = ['docker run', image_name] + arg_lst
    cmd = ' '.join(cmd)
    os.system(cmd)
    return 'done\n'

if __name__ == '__main__':
    app.run(host='0.0.0.0')
