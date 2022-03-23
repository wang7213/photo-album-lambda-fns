import math
import dateutil.parser
import datetime
import time
import os
import logging
import json
import boto3
import requests
import requests_aws4auth
from opensearchpy import OpenSearch, RequestsHttpConnection


lex = boto3.client('lex-runtime')

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

credentials = boto3.Session().get_credentials()
awsauth = requests_aws4auth.AWS4Auth(credentials.access_key, credentials.secret_key, 'us-east-1', 'es', session_token=credentials.token)
os_url = 'search-photos-3rwlsmhe6qy5kthcpzzktyalnm.us-east-1.es.amazonaws.com'
os_instance = OpenSearch(hosts = [{'host': os_url, 'port': 443}],
                         http_auth = awsauth,
                         use_ssl = True,
                         verify_certs = True,
                         connection_class = RequestsHttpConnection)
                         
def search_opensearch(keywords):
    to_return = []
    seen = set()
    lower_list = [word.lower() for word in keywords]

    # each keyword must appear in the labels list
    query = {
        'query': {
            'bool': {
                'must': [{'match': {'labels': word}} for word in lower_list]
            }
        }
    }
    results = os_instance.search(index="photos", body=query)
    for res in results['hits']['hits']:
        key = res['_source']['objectKey']
            
        # don't redisplay any images we've already seen
        if key in seen:
            continue
        seen.add(key)
        to_return.append({'url': 'https://columbia-hw2-photos.s3.amazonaws.com/' + key, 'labels': res['_source']['labels']})
            
        # only get up to 10 results
        if len(to_return) > 10:
            break

    print(to_return)
    return to_return

# this is a hacky way to "depluralize" queries
def depluralize(labels):
    singulars = []
    for label in labels:
        new_string = label
        if label[-1] == 's':
            new_string = label[:-1]
        singulars.append(new_string)
    return singulars
        
def lambda_handler(event, context):
    query = event['q']
    response = lex.post_text(botName='KeywordsDetectBot',
                             botAlias='detector',
                             userId='testuser',
                             inputText=query)
    print(response)
    
    data = []
    dialogState = response['dialogState']
    if dialogState == 'ReadyForFulfillment':
        keywords = []
        label1 = response['slots']["label_one"]
        label2 = response['slots']["label_two"]
        print(label1)
        print(label2)
        keywords.append(label1)
        if label2 is not None:
            keywords.append(label2)
        data = search_opensearch(depluralize(keywords))
    else:
        print("No label detected")
        
    return {
        'statusCode': 200,
        'results': data
    }
