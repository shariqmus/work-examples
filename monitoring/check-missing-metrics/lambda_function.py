#
#
# AWS Lambda Python script to query for Cloudwatch metrics for all running
# EC2 instance and if unavailable send a message through an SNS topic
# to check for EC2Config service
#
# Required IAM permissions:
#   ec2:DescribeInstances
#   sns:Publish
#   cloudwatch:GetMetricStatistics
#   dynamodb: Read/Write to CWCheckData Table
#
# Setup:
# Check these in the code (Search *1 and *2):
#   *1 : Confirm details of the parameters
#   *2 : Confirm details of the dimensions
#   Define Environment Variable "CustomerID" while creating Lambda function

from __future__ import print_function
import boto3
import sys
import os
from calendar import timegm
from datetime import datetime, timedelta
import json
import decimal
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError

class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            if o % 1 > 0:
                return float(o)
            else:
                return int(o)
        return super(DecimalEncoder, self).default(o)

def dynamodb_create_table():
    dynamodb = boto3.resource('dynamodb')

    table = dynamodb.create_table(
        TableName='CWCheckData',
        KeySchema=[
            {
                'AttributeName': 'instance_id',
                'KeyType': 'HASH'  #Partition key
            }
        ],
        AttributeDefinitions=[
            {
                'AttributeName': 'instance_id',
                'AttributeType': 'S'
            }

        ],
        ProvisionedThroughput={
            'ReadCapacityUnits': 5,
            'WriteCapacityUnits': 5
        }
    )

    print("CW_Missing_Metrics: Table status:", table.table_status)

# Get one value from table
def dynamodb_get_single_value(table_name, qry_col_name, qry_col_value, rslt_col_name):

    ret_value = ""

    _region = "ap-southeast-2"  # Region
    dynamodb = boto3.resource("dynamodb", _region)

    table = dynamodb.Table(table_name)

    try:
        response = table.query(
            KeyConditionExpression=Key(qry_col_name).eq(qry_col_value)
        )

    except ClientError as e:
        print("CW_Missing_Metrics: Error (dynamodb_get_single_value): ", e.response['Error']['Message'])
    else:
        for i in response['Items']:
            ret_value = i[rslt_col_name]

    return ret_value

# Set one value from table
def dynamodb_set_single_value(table_name, upd_col_name, upd_col_value, new_col_name, new_col_value):

    _region = "ap-southeast-2"  # Region
    dynamodb = boto3.resource("dynamodb", _region)

    table = dynamodb.Table(table_name)

    try:
        response = table.update_item(
            Key={
                upd_col_name: upd_col_value
            },
            UpdateExpression="set {0} = :b".format(new_col_name),
            ExpressionAttributeValues={
                ':b': new_col_value
            },
            ReturnValues="UPDATED_NEW"
        )
    except ClientError as e:
        print("CW_Missing_Metrics: Error (dynamodb_set_single_value): ", e.response['Error']['Message'])
    else:
        print("CW_Missing_Metrics: Successfully added/updated record to new value")

def check_tag_present_x(instance, tag_name):
    temp_tags = ""
    for tag in instance.tags:
        if tag['Key'] == tag_name:
            return True

    return False


def check_tag_present(instance, tag_name, tag_value):
    for tag in instance.tags:
        if tag['Key'] == tag_name:
            if tag['Value'] == tag_value:
                return True

    return False

def send_alert(list_instances, topic_arn):
    if topic_arn == "":
        print("CW_Missing_Metrics: Missing topic ARN. Returning without sending alert.")
        return

    instances = ""

    for s in list_instances:
        instances += s
        instances += "\n\n"

    subject = os.getenv('CustomerID', '') + " - Warning: Missing CloudWatch metric data"
    message = "Warning: Missing CloudWatch metric data for the following instance id(s): \n\n" + instances + "Check the EC2Config service is running and the config file in C:\\Program Files\\Amazon\\Ec2ConfigService\\Settings is correct."

    print("CW_Missing_Metrics: *** Sending alert ***")
    print("CW_Missing_Metrics: Message: {0}".format(message))

    client = boto3.client('sns')
    response = client.publish(TargetArn=topic_arn, Message=message, Subject=subject)

def lambda_handler(event, context):

    # *1-Provide the following information
    _instancetagname = 'Environment'  # Main filter Tag key
    _instancetagvalue = 'PROD'  # Main filter Tag value
    _period = int(10)  # Period in minutes
    _namespace = 'WindowsPlatform'  # Namespace of metric
    _metricname = 'Available Memory'  # Metric name
    _unit = 'Megabytes'  # Unit
    _topicarn = 'arn:aws:sns:ap-southeast-2:862017364710:CloudWatchMissingMetrics'  # SNS Topic ARN to write message to
    _min_minutes = 1440  # Max minutes to wait before sending next alert for an instance, One Day = 1440 minutes
    _region = "ap-southeast-2"  # Region

    ec2 = boto3.resource('ec2', _region)
    cw = boto3.client('cloudwatch', _region)

    filters = [{'Name': 'instance-state-name', 'Values': ['running']}]

    instances = ec2.instances.filter(Filters=filters)

    now = datetime.now()

    print("CW_Missing_Metrics: Reading Cloud watch metric for last {0} minutes.".format(_period))

    start_time = datetime.utcnow() - timedelta(minutes=_period)
    end_time = datetime.utcnow()

    print("CW_Missing_Metrics: List of running instances:")

    list_instances = []

    for instance in instances:

        if check_tag_present(instance, _instancetagname, _instancetagvalue) == False:
            # print ("Tag/Value missing, ignoring instance ", instance.id)
            continue

        cwTag = "Cloudwatch Server Name"
        if check_tag_present_x(instance, cwTag) == False:  # Tag missing, ignore
            # print ("***** Tag ", cwTag, " missing, ignoring instance ", instance.id)
            continue

        print("CW_Missing_Metrics: Checking ", instance.id)

        i = 1

        date_s = instance.launch_time
        date_s = date_s.replace(tzinfo=None)
        # date_s = datetime.datetime.now(date_s.tzinfo)
        new_dt = datetime.utcnow() - date_s

        instance_name = [tag['Value'] for tag in instance.tags if tag['Key'] == 'Name'][0]
        cw_server_name = [tag['Value'] for tag in instance.tags if tag['Key'] == 'Cloudwatch Server Name'][0]
        cw_server_name = cw_server_name.lower()
        minutessince = int(new_dt.total_seconds() / 60)

        # print("Instance id:",instance.id)
        # print("Instance name:",instance_name)
        # print("Launch time:",instance.launch_time)
        # print("Instance uptime:",minutessince,"min\n")

        if minutessince < _period:
            print("CW_Missing_Metrics: Not looking for data on this instance as uptime is less than requested period.")
            continue

        metrics = cw.get_metric_statistics(
            Namespace=_namespace,
            MetricName=_metricname,
            Dimensions=[{'Name': 'Server Name', 'Value': cw_server_name}],
            # Dimensions=[{'Name': 'InstanceId','Value': instance.id}], # *2
            StartTime=start_time,
            EndTime=end_time,
            Period=300,
            Statistics=['Maximum'],
            Unit=_unit
        )

        datapoints = metrics['Datapoints']
        # print("datapoints array=====>", datapoints)

        for datapoint in datapoints:
            if datapoint['Maximum']:
                # print i,")\nInstance name:",instance_name,"\nInstance id:",instance.id,"\nDatapoint Data:",datapoint['Maximum'],"\nTimeStamp: ",datapoint['Timestamp'],"\n=============================\n"
                print(i, ")\nDatapoint Data:", datapoint['Maximum'], "\nTimeStamp: ", datapoint['Timestamp'], "\n")
                i += 1
            else:
                print("CW_Missing_Metrics: Cloudwatch has no Maximum metrics for", _metricname, "instance id: ", instance.id)

        if i == 1:  # No data point found
            # print ("Data points not found.")
            print("CW_Missing_Metrics: Cloudwatch has no metrics for", _metricname, " for instance id: ", instance.id)
            list_instances.append(instance_name + " (" + instance.id + ")" + ", CW Server Name: " + cw_server_name)

        print("=================================================\n")

    #DEBUG
    #list_instances.append('i-0a25dc7ba6b4a5d3b')

    list_instances_for_alert = []

    for s in list_instances: # these instances in 'list_instances' have missing metrics

        # Check if instance was reported in last 24 hr
        last_checked = dynamodb_get_single_value("CWCheckData", "instance_id", s, "last_checked")

        if (last_checked == ""):
            print ("CW_Missing_Metrics: First alert for Instance {0}.".format(s))
            fmt = '%Y%m%d%H%M%S'  # ex. 20110104172008 -> Jan. 04, 2011 5:20:08pm
            now_str = datetime.now().strftime(fmt)

            # Set alert sending date in DB
            dynamodb_set_single_value("CWCheckData", "instance_id", s, "last_checked", now_str)
            list_instances_for_alert.append(s)

        else:
            fmt = '%Y%m%d%H%M%S'  # ex. 20110104172008 -> Jan. 04, 2011 5:20:08pm
            now_str = datetime.now().strftime(fmt)
            rec_datetime = datetime.strptime(last_checked, fmt)
            rec_datetime = rec_datetime.replace(tzinfo=None)
            now_datetime = datetime.strptime(now_str, fmt)
            new_dt = now_datetime - rec_datetime
            min_last_alert= int(new_dt.total_seconds() / 60)

            if (min_last_alert > _min_minutes):
                # Set alert sending date in DB
                print("CW_Missing_Metrics: New alert for Instance {0}.".format(s))
                dynamodb_set_single_value("CWCheckData", "instance_id", s, "last_checked", now_str)
                list_instances_for_alert.append(s)
            else:
                print("CW_Missing_Metrics: Alert already sent for instance '{0}' within last {1} minutes.".format(s, _min_minutes))

    if len(list_instances_for_alert) > 0:
        send_alert(list_instances_for_alert, _topicarn)

################################ Main ################################

#boto3.setup_default_session(profile_name='vicroads')
#print ('CW_Missing_Metrics: Loading function...')
#lambda_handler(0,0)
#dynamodb_create_table()
#dynamodb_get_single_value("CWCheckData", "instance_id", "i-0de559fcf8bfd5053-1", "last_checked")
#dynamodb_set_single_value("CWCheckData", "instance_id", "i-0de559fcf8bfd5053-1", "last_checked", "DDDDDDD")

################################ Main ################################
