# This Lambda fucntion creates "Status Check Failed Instance" Metric and Alram with Restart action for any EC2 instance in the region.
# This Lambda fucntion creates "Status Check Failed System" Metric and Alram with Recover action for any EC2 instance in the region.
# Before running the function please review the SNS Topic, Account ID (akid) and Region.
# The Lambda Role has full access to Ec2 and Cloudwatch via policy

import os
import boto3
import collections
import json

#SNS Topic Definition for EC2
ec2_sns = os.environ['ec2_sns']

#AWS Account and Region Definition for Reboot Actions
akid = os.environ['accountid']
region = os.environ['region']

#Create AWS clients
ec = boto3.client('ec2')
cw = boto3.client('cloudwatch')

def lambda_handler(event, context):

    #Enumerate EC2 instances
    reservations = ec.describe_instances().get('Reservations', [])
    instances = sum(
        [
            [i for i in r['Instances']]
            for r in reservations
        ], [])

    for instance in instances:
        try:
            for tag in instance['Tags']:
                if tag['Key'] == 'Name':
                    name_tag = tag['Value']
                    print "Found instance %s with name %s" % (instance['InstanceId'], name_tag)
                    #Create Metric "Status Check Failed (System) for 5 Minutes"
                    response = cw.put_metric_alarm(
                        AlarmName="TMS - %s %s System Check Failed" % (name_tag, instance['InstanceId']),
                        AlarmDescription='TMS - Status Check Failed (System) for 5 Minutes',
                        ActionsEnabled=True,
                        AlarmActions=[
                            ec2_sns,
                            "arn:aws:automate:%s:ec2:recover" % region,
                            ],
                            MetricName='StatusCheckFailed_System',
                            Namespace='AWS/EC2',
                            Statistic='Average',
                            Dimensions=[{'Name': 'InstanceId','Value': instance['InstanceId']},],
                            Period=60,
                            EvaluationPeriods=5,
                            Threshold=1.0,
                            ComparisonOperator='GreaterThanOrEqualToThreshold'
                            )
                    #Create Metric "Status Check Failed (Instance) for 5 Minutes"
                    response = cw.put_metric_alarm(
                        AlarmName="TMS - %s %s Instance Check Failed" % (name_tag, instance['InstanceId']),
                        AlarmDescription='TMS - Status Check Failed (Instance) for 5 Minutes',
                        ActionsEnabled=True,
                        AlarmActions=[
                        ec2_sns,
                        "arn:aws:swf:%s:%s:action/actions/AWS_EC2.InstanceId.Reboot/1.0" % (region, akid)
                        ],
                        MetricName='StatusCheckFailed_Instance',
                        Namespace='AWS/EC2',
                        Statistic='Average',
                        Dimensions=[{'Name': 'InstanceId','Value': instance['InstanceId']},],
                        Period=60,
                        EvaluationPeriods=5,
                        Threshold=1.0,
                        ComparisonOperator='GreaterThanOrEqualToThreshold'
                        )
        except Exception, e:
            print ("Error Encountered.")
            print (e)
