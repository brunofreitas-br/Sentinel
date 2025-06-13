import boto3
import gzip
import json
import io
import os
import urllib.request
import urllib.parse
import time
import random
from datetime import datetime

# Environment variables
AZURE_TENANT_ID = os.environ['AZURE_TENANT_ID']
AZURE_CLIENT_ID = os.environ['AZURE_CLIENT_ID']
AZURE_CLIENT_SECRET = os.environ['AZURE_CLIENT_SECRET']
AZURE_DCE_URL = os.environ['AZURE_DCE_URL']
AZURE_DCR_NAMES = os.environ['AZURE_DCR_NAMES'].split(",")  # List of DCRs, e.g., dcr-abc,dcr-def
AZURE_STREAM_NAME = os.environ['AZURE_STREAM_NAME']

MAX_RECORDS = 500
MAX_PAYLOAD_SIZE = 950 * 1024
MAX_RETRIES = 3
MAX_FIELD_SIZE = 64 * 1024


# Retrieves an OAuth 2.0 token using client credentials to authenticate with Azure Monitor
def get_azure_token():
    url = f"https://login.microsoftonline.com/{AZURE_TENANT_ID}/oauth2/v2.0/token"
    data = urllib.parse.urlencode({
        'grant_type': 'client_credentials',
        'client_id': AZURE_CLIENT_ID,
        'client_secret': AZURE_CLIENT_SECRET,
        'scope': 'https://monitor.azure.com/.default'
    }).encode('utf-8')
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req) as res:
        response = json.loads(res.read().decode())
        print("[INFO] Token Azure obtido com sucesso.")
        return response['access_token']


# Reads and decompresses the specified .json.gz file from S3
def process_file(bucket, key):
    print(f"[INFO] Lendo arquivo: s3://{bucket}/{key}")
    s3 = boto3.client('s3')
    response = s3.get_object(Bucket=bucket, Key=key)
    with gzip.GzipFile(fileobj=response['Body']) as f:
        raw_data = f.read().decode('utf-8')
    data = json.loads(raw_data)
    records = data.get("Records", [])
    print(f"[INFO] {len(records)} eventos extraídos do arquivo.")
    return records


def truncate_string(s):
    return s[:MAX_FIELD_SIZE] if len(s) > MAX_FIELD_SIZE else s


# Maps CloudTrail event fields to the schema expected by the Sentinel table
def map_event_fields(event):
    # Map CloudTrail fields into the structure expected by the Sentinel table schema
    def safe_get(path, default=""):
        keys = path.split(".")
        val = event
        try:
            for k in keys:
                val = val[k]
            return val
        except:
            return default

    return {
        "TimeGenerated": event.get("eventTime", datetime.utcnow().isoformat() + "Z"),
        "AwsEventId": event.get("eventID", ""),
        "EventVersion": event.get("eventVersion", ""),
        "EventSource": event.get("eventSource", ""),
        "EventTypeName": event.get("eventType", ""),
        "EventName": event.get("eventName", ""),
        "UserIdentityType": safe_get("userIdentity.type"),
        "UserIdentityPrincipalid": safe_get("userIdentity.principalId"),
        "UserIdentityArn": safe_get("userIdentity.arn"),
        "UserIdentityAccountId": safe_get("userIdentity.accountId"),
        "UserIdentityAccessKeyId": safe_get("userIdentity.accessKeyId"),
        "UserIdentityUserName": safe_get("userIdentity.userName"),
        "AWSRegion": event.get("awsRegion", ""),
        "SourceIpAddress": event.get("sourceIPAddress", ""),
        "UserAgent": event.get("userAgent", ""),
        "RequestParameters": truncate_string(json.dumps(event.get("requestParameters", {}))),
        "ResponseElements": truncate_string(json.dumps(event.get("responseElements", {}))),
        "RecipientAccountId": event.get("recipientAccountId", ""),
        "UserIdentityInvokedBy": event.get("userIdentity", {}).get("invokedBy"),
        "SessionMfaAuthenticated": event.get("sessionContext", {}).get("attributes", {}).get("mfaAuthenticated") == "true",
        "SessionCreationDate": event.get("sessionContext", {}).get("attributes", {}).get("creationDate"),
        "SessionIssuerType": event.get("sessionContext", {}).get("sessionIssuer", {}).get("type"),
        "SessionIssuerPrincipalId": event.get("sessionContext", {}).get("sessionIssuer", {}).get("principalId"),
        "SessionIssuerArn": event.get("sessionContext", {}).get("sessionIssuer", {}).get("arn"),
        "SessionIssuerAccountId": event.get("sessionContext", {}).get("sessionIssuer", {}).get("accountId"),
        "SessionIssuerUserName": event.get("sessionContext", {}).get("sessionIssuer", {}).get("userName"),
        "ErrorCode": event.get("errorCode"),
        "ErrorMessage": event.get("errorMessage"),
        "AdditionalEventData": json.dumps(event.get("additionalEventData", {})),
        "AwsRequestId": event.get("requestID"),
        "AwsRequestId_": event.get("requestId"),
        "Resources": json.dumps(event.get("resources", {})),
        "APIVersion": event.get("apiVersion"),
        "ReadOnly": event.get("readOnly"),
        "ServiceEventDetails": json.dumps(event.get("serviceEventDetails", {})),
        "SharedEventId": event.get("sharedEventID"),
        "VpcEndpointId": event.get("vpcEndpointId"),
        "ManagementEvent": event.get("managementEvent"),
        "SourceSystem": event.get("sourceSystem"),
        "OperationName": event.get("operationName"),
        "Category": event.get("category"),
        "EC2RoleDelivery": event.get("ec2RoleDelivery"),
        "TlsVersion": event.get("tlsDetails", {}).get("tlsVersion"),
        "CipherSuite": event.get("tlsDetails", {}).get("cipherSuite"),
        "ClientProvidedHostHeader": event.get("tlsDetails", {}).get("clientProvidedHostHeader"),
        "IpProtocol": event.get("networkDetails", {}).get("ipProtocol"),
        "SourcePort": event.get("networkDetails", {}).get("sourcePort"),
        "DestinationPort": event.get("networkDetails", {}).get("destinationPort"),
        "CidrIp": event.get("networkDetails", {}).get("cidrIp"),
        "RawEvent": truncate_string(json.dumps(event))
    }


# Sends events to Azure Monitor Logs Ingestion API, rotating across DCRs if needed
def send_to_dce(token, events):
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    batch = []

    def flush(selected_dcr):
        if not batch:
            return
        payload = json.dumps(batch).encode('utf-8')
        dcr_list = [selected_dcr] + [d for d in AZURE_DCR_NAMES if d != selected_dcr]  # Prioritize initially selected DCR

        for dcr in dcr_list:
            endpoint = f"{AZURE_DCE_URL}/dataCollectionRules/{dcr}/streams/{AZURE_STREAM_NAME}?api-version=2021-11-01-preview"
            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    print(f"[INFO] Enviando {len(batch)} eventos para {dcr}, tentativa {attempt}")
                    req = urllib.request.Request(endpoint, data=payload, headers=headers, method='POST')
                    with urllib.request.urlopen(req) as res:
                        print(f"[SUCCESS] Enviado com status: {res.status}")
                        response_body = res.read().decode()
                        if response_body:
                            print(f"[DEBUG] Resposta: {response_body}")
                        batch.clear()
                        return
                except urllib.error.HTTPError as e:
                    retry_after = int(e.headers.get('Retry-After', '5'))
                    print(f"[WARN] Falha {e.code} - Retry-After: {retry_after}s")
                    time.sleep(retry_after + attempt * 2)
                except Exception as ex:
                    print(f"[ERROR] Erro inesperado ao enviar: {str(ex)}")
                    time.sleep(attempt * 2)
            print(f"[WARN] Tentativas esgotadas com DCR {dcr}, tentando próxima se disponível.")
        print("[ERROR] Todas as DCRs falharam para este batch.")
        batch.clear()

    for event in events:
        record = map_event_fields(event)
        batch.append(record)
        if len(batch) >= MAX_RECORDS or len(json.dumps(batch).encode("utf-8")) > MAX_PAYLOAD_SIZE:
            selected_dcr = random.choice(AZURE_DCR_NAMES)
            flush(selected_dcr)

    if batch:
        selected_dcr = random.choice(AZURE_DCR_NAMES)
        flush(selected_dcr)


# Main Lambda handler triggered by SQS events
# It processes S3 object notifications and sends CloudTrail records to Sentinel
def lambda_handler(event, context):
    print("[INFO] Lambda acionada.")
    token = get_azure_token()

    for record in event['Records']:
        try:
            message = json.loads(record['body'])
            s3_info = message['Records'][0]['s3']
            bucket = s3_info['bucket']['name']
            key = s3_info['object']['key']
            print(f"[INFO] Processando objeto S3: {key}")

            events = process_file(bucket, key)
            send_to_dce(token, events)

        except Exception as e:
            print(f"[EXCEPTION] Erro ao processar registro do SQS: {str(e)}")
