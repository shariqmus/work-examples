#
#
# AWS Lambda Python script to query for EC2 Instances that have ssecurity group
# with specific port allowed. Currently we require it to check RDP port
# being open 
#
# Required IAM permissions:
#   ec2:DescribeInstances
#   ec2:DescribeSecurityGroups 
#   sns:Publish
#
# Setup:
# Need to provide the following via Environment variables
# They are all optional 
#    - TagKey1
#    - TagValue1
#    - TagKey2
#    - TagValue2
#    - TagKey3
#    - TagValue3
#    - Port
#    - SNSTopic
#    - ClientId
#

from __future__ import print_function
import boto3
import json
from botocore.exceptions import ClientError
import sys
import os

# Get ALL security groups names

ec2 = boto3.client('ec2')
clientsecgrps = ec2.describe_security_groups()
groups = clientsecgrps['SecurityGroups']

# Can provide upto 3 Tag Key/Value pair
envTagKey1 = os.getenv('TagKey1', '')
envTagVal1 = os.getenv('TagVal1', '')
envTagKey2= os.getenv('TagKey2', '')
envTagVal2= os.getenv('TagVal2', '')
envTagKey3 = os.getenv('TagKey3', '')
envTagVal3 = os.getenv('TagVal3', '')

envPort = int(os.getenv('Port', '3389'))
envSNSTopic = os.getenv('SNSTopic', '')
envClientId = os.getenv('ClientId', '')

def send_alert(msg, topic_arn):
    
    if topic_arn == "":
        return

    subject = envClientId + " - Warning: Found Open " + str(envPort) + " Port on Instance(s)"
    message = "Warning: Found Open " + str(envPort) + " Port on Instance(s). See details below. Please refer to Service Request wiki page for customer to resolve the service request. \n\n" + msg 
    client = boto3.client('sns')
    response = client.publish(TargetArn=topic_arn,Message=message,Subject=subject)

def check_tag_present(instance, tag_name, tag_value):

    tags = instance['Tags']
    for tag in tags:
        if tag['Key'] == tag_name:
            if tag['Value'] == tag_value:
                return True
 
    return False

def get_instance_name(instance):

    tags = instance['Tags']
    for tag in tags:
        if tag['Key'] == 'Name':
            return tag['Value']

    return '' 

def CheckSecGroupPort(GroupId, Port):

    tempstr = ""
    ret = ""
    
    for group in groups:
        if group['GroupId'] == GroupId:
            if len(group['IpPermissions']) > 0:            
                for permission in group['IpPermissions']:
                    ipp = permission['IpProtocol']
                    ipr = permission['IpRanges']
                    uidgps = permission['UserIdGroupPairs']
                    plis = permission['PrefixListIds']
                    if 'ToPort' in permission.keys():
                        if (int(permission['ToPort']))==Port:
                            tempstr = "Inbound "
                            ret += tempstr
                            continue

            # if len(group['IpPermissionsEgress']) > 0:
                # for permission in group['IpPermissionsEgress']:
                    # ipp = permission['IpProtocol']
                    # ipr = permission['IpRanges']
                    # uidgps = permission['UserIdGroupPairs']
                    # plis = permission['PrefixListIds']
                    # if 'ToPort' in permission.keys():
                        # if (int(permission['ToPort']))==Port:
                            # tempstr = "Outbound "
                            # ret += tempstr
                            # continue

    return ret

def lambda_handler(event, context):

    msg = ""
    count = 0

    inst_name = []
    inst_id = []
    secg = []
    access = []

    for reservation in boto3.client('ec2').describe_instances()['Reservations']:
        for instance in reservation['Instances']:
        
            tag_present = 0

            # Check tags are present, atleast one should be present to check the instance
            if envTagKey1 != "":
                if check_tag_present(instance, envTagKey1, envTagVal1)==True:
                    tag_present = tag_present + 1

            if envTagKey2 != "":
                if check_tag_present(instance, envTagKey2, envTagVal2)==True:
                    tag_present = tag_present + 1

            if envTagKey3 != "":
                if check_tag_present(instance, envTagKey3, envTagVal3)==True:
                    tag_present = tag_present + 1

            if tag_present == 0:
                if envTagKey1 == "" and envTagKey2 == "" and envTagKey3 == "": # Not providing any key so all included
                    pass
                else:
                    continue

            # Enumerate sec groups
            for sg in instance.get('SecurityGroups', []):
                sgp = CheckSecGroupPort(sg['GroupId'],envPort)
                if sgp != "" :
                    inst_name.append(get_instance_name(instance))
                    inst_id.append(instance['InstanceId'])                        
                    secg.append(sg['GroupName'])
                    access.append(sgp)
                    count = count+1

    # Print as table
    titles = ['Inst Name', 'Inst Id', 'Sec Grp', 'Access']
    data = [titles] + list(zip(inst_name, inst_id, secg, access))

    for i, d in enumerate(data):
        line = '| '.join(str(x).ljust(20) for x in d)
        print(line)
        msg += line + "\n"
        
        if i == 0:
            print('-' * len(line))
            msg += '-' * len(line) + "\n"

    if count > 0:
        send_alert(msg, envSNSTopic)

#lambda_handler(0,0)