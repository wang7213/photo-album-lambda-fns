import json
import urllib.parse
import boto3
import datetime
import requests
import requests_aws4auth
from opensearchpy import OpenSearch, RequestsHttpConnection

print('Loading function')

credentials = boto3.Session().get_credentials()
awsauth = requests_aws4auth.AWS4Auth(credentials.access_key, credentials.secret_key, 'us-east-1', 'es', session_token=credentials.token)
os_url = 'search-photos-3rwlsmhe6qy5kthcpzzktyalnm.us-east-1.es.amazonaws.com'
os_instance = OpenSearch(hosts = [{'host': os_url, 'port': 443}],
                         http_auth = awsauth,
                         use_ssl = True,
                         verify_certs = True,
                         connection_class = RequestsHttpConnection)

s3 = boto3.client('s3')
rekog = boto3.client("rekognition")

def lambda_handler(event, context):
    print("Event: " + json.dumps(event))

    # get the bucket and key from the event
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = urllib.parse.unquote_plus(record['object']['key'], encoding='utf-8')

    # get the optional custom labels
    labels = []
    head_response = s3.head_object(Bucket=bucket, Key=key)
    print("Head object: " + str(head_response))
    if 'Metadata' in head_response and 'customlabels' in head_response['Metadata']:
        custom_labels = head_response['Metadata']['customlabels']
        labels_tmp = custom_labels.strip().split(',')
        for label in labels_tmp:
            label = label.strip()
            if len(label) != 0:
                labels.append(label.lower())

    # send the image to rekognition and get back any identified labels
    rekog_response = rekog.detect_labels(Image = {"S3Object": {"Bucket": bucket, "Name": key}})
    for label_entry in rekog_response["Labels"]:
        labels.append(label_entry["Name"].lower())

    print(labels)
    
    # add an entry to elasticsearch
    entry = {
        "objectKey": key,
        "bucket": bucket,
        "createdTimestamp": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "labels": labels
    }
    
    os_instance.index(index="photos", doc_type="_doc", id=key, body=entry)
    print(os_instance.get(index="photos", doc_type="_doc", id=key)) # verify successful entry
