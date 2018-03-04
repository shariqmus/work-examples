# This script look for missing tags on EC2 instances
# Initialize 5 Environment variables tag1...tag5
# Usual tags to check can be as follows
#  - cpm backup
#  - monitor_site24x7
#  - Project
#  - Environment
#  - Owner

import boto3
import logging
import os

lambda_func_name = os.getenv("AWS_LAMBDA_FUNCTION_NAME", "")

if lambda_func_name == "": # We are not running in AWS
    boto3.setup_default_session(profile_name='iconwater')

# setup simple logging for INFO
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# define the connection
ec2 = boto3.resource('ec2')

def send_alert(alert_data):
    
    topic_arn = os.getenv("TopicARN", "")
        
    if topic_arn == "":
        print("send_alert: Missing topic ARN. Returning without sending alert.")
        return

    subject = os.getenv('CustomerID', '') + " - Missing EC2 Instances Tag Check"
    message = "Missing EC2 Instances Tag Check Results: \n\n" + alert_data

    print("send_alert: *** Sending alert ***")
    print("send_alert: Message: {0}".format(message))

    client = boto3.client('sns')
    response = client.publish(TargetArn=topic_arn, 
                              Message=message, 
                              Subject=subject)

def find_instances_with_missing_tags(tag_to_check):

    result_str = ""

    client = boto3.client('ec2')

    client = boto3.client('ec2', region_name='ap-southeast-2')
    # Check running or stopped instances
    response = client.describe_instances(
        Filters=[
            {
                'Name': 'instance-state-name',
                'Values': ['running', 'stopped']
            }
        ])
    # Iterate over instance(s)
    for r in response['Reservations']:
        for inst in r['Instances']:
            inst_id = inst['InstanceId']
            tags = inst['Tags']
            # Check the Name tag
            for tag in tags:
                if 'Name' in tag['Key']:
                    ins_name = (tag['Value'])
                    break
                else:
                    ins_name = "{No-Name}"

            for tag in tags:
                if tag_to_check in tag['Key']:
                    ins_tag = (tag['Value'])
                    break
                else:
                    ins_tag = "NA"

            if ins_tag == "NA":
                s = "Tag '{}' missing for instance {} ({})\n\n".format(tag_to_check, ins_name, inst['InstanceId'])
                #print (s)
                result_str = result_str + s
            #else:
            #    print("Tag '{}' present for instance {} ({})".format(tag_to_check, ins_name, inst['InstanceId']))

    return result_str

def lambda_handler(event, context):
    
    tag1 = os.getenv("tag1", "")
    tag2 = os.getenv("tag2", "")
    tag3 = os.getenv("tag3", "")
    tag4 = os.getenv("tag4", "")
    tag5 = os.getenv("tag5", "")

    s = ""

    if tag1 != "": s = s + find_instances_with_missing_tags(tag1)
    if tag2 != "": s = s + find_instances_with_missing_tags(tag2)
    if tag3 != "": s = s + find_instances_with_missing_tags(tag3)
    if tag4 != "": s = s + find_instances_with_missing_tags(tag4)
    if tag5 != "": s = s + find_instances_with_missing_tags(tag5)

    if s != "":
        print(s)
        send_alert(s)

    return 0

if __name__ == "__main__":
    lambda_handler(0, 0)
