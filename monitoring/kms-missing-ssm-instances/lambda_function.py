# This script look for Instances not reporting/online in SSM

import boto3
import os

lambda_func_name = os.getenv("AWS_LAMBDA_FUNCTION_NAME", "")

if lambda_func_name == "":  # We are not running in AWS
    boto3.setup_default_session(profile_name='iconwater')

ec2 = boto3.resource('ec2')

instances_missing_in_ssm = []

def send_alert():
    
    alert_data = ""
    
    topic_arn = os.getenv("TopicARN", "")

    if topic_arn == "":
        print("send_alert: Missing topic ARN. Returning without sending alert.")
        return

    for m in instances_missing_in_ssm:
        alert_data  = alert_data + m +"\n\n"

    subject = os.getenv('CustomerID', '') + " - Missing Managed (SSM) Instances"
    message = "The following instances are offline or not reporting to SSM: \n\n" + alert_data

    print("send_alert: *** Sending alert ***")
    print("send_alert: Message: {0}".format(message))

    client = boto3.client('sns')
    response = client.publish(TargetArn=topic_arn,
                              Message=message,
                              Subject=subject)

def check_instance_ssm_status(instance_id):

    #print ("Checking {}".format(instance_id))

    client_ssm = boto3.client('ssm', region_name='ap-southeast-2')
    # Check running or stopped instances
    response = client_ssm.describe_instance_information(
        InstanceInformationFilterList=[
            {
                'key': 'InstanceIds',
                'valueSet': [
                    instance_id,
                ]
            },
        ]
    )

    #print (response)

    for r in response['InstanceInformationList']:
        #print(r)
        return r['PingStatus']

def find_instances_not_with_ssm():
    result_str = ""

    client_ec2 = boto3.client('ec2', region_name='ap-southeast-2')
    # Check running or stopped instances
    response = client_ec2.describe_instances(
        Filters=[
            {
                'Name': 'instance-state-name',
                'Values': ['running'] # SM - Removing on 25/02/2018 =>    , 'stopped'
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

            inst_id = inst['InstanceId']
            ssm_status = check_instance_ssm_status(inst_id)

            if ssm_status != 'Online':
                instances_missing_in_ssm.append(ins_name + " (" + inst_id + ")")

            #s = "{} ({})".format(ins_name, inst['InstanceId'])

    return len(instances_missing_in_ssm)

def lambda_handler(event, context):

    ret = find_instances_not_with_ssm()

    if (ret > 0):
        send_alert()

    return 0

if __name__ == "__main__":
    lambda_handler(0, 0)
