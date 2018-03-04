###############################
#
# Monitor IP addresses free in subnet
# Kloud Solutions
# Creates custom metric for free IPs in Subnets
# Set in Environment Variable
#
# CW Alarms can be set to detect IP Exhaustion
# Useful for VPC-deployed Lambda Functions
# And Capacity Monitoring
#
################################
import logging
import boto3
import json
import os

logger = logging.getLogger()
logger.setLevel(logging.INFO)


cwclient = boto3.client('cloudwatch')
ec2 = boto3.client("ec2")

def lambda_handler ( event, context ):
    #Get Filter from Environment Variables:
    subnetstomonitor = os.getenv('SubnetsToMonitor', '')
    #Remove any spaces and then split by comma
    subnetlist=os.environ.get("SubnetsToMonitor")
    subnetlist=subnetlist.replace(" ", "")
    subnetlist=subnetlist.split(",")
    ec2 = boto3.client("ec2")
    response=response = ec2.describe_subnets(Filters=[{'Name': 'subnet-id','Values': subnetlist}])
    #print(response['Subnets'])
    data=response['Subnets']
    ver_subnets  (response)


# virtualInterfaces payload evaluation
def ver_subnets ( data ):
    if not 'Subnets' in data:
        logger.error("unexpected: Subnets key not found in data")
        return
    for subnet in data['Subnets']:
        put_subnetmetric( subnet['SubnetId'],subnet['AvailableIpAddressCount'] )


# Writes VirtualInterfaceState dimension data to DX custom metric
def put_subnetmetric ( subnetid, availaddresscount ):
    response = cwclient.put_metric_data(
        Namespace='AWSx/SubnetCapacity',
        MetricData=[
            {
                'MetricName': 'AvailableIPAddresses',
                'Dimensions': [
                    {
                        'Name': 'SubnetId',
                        'Value': subnetid
                    },
                ],
                'Value': availaddresscount,
                'Unit': 'None'
            },
        ],
    )