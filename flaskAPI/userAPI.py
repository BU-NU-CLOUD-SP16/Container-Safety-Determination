from elasticsearch import Elasticsearch
import json
from flask import * 
app = Flask(__name__)

@app.route('/get_suspicious')
def test2():
    es = Elasticsearch('10.10.10.15:9200')
    res_index = es.search(index = 'judgeresult:ubuntu:latest')
    res_lst = []
    for item in res_index['hits']['hits']:
        res_lst.append(item['_source']['file'])
    json_res = json.dumps(res_lst)
    return json_res

if __name__ == '__main__':
    app.run()
