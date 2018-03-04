import boto3
import os
from time import sleep

lambda_func_name = os.getenv("AWS_LAMBDA_FUNCTION_NAME", "")

if lambda_func_name == "":  # We are not running in AWS
    boto3.setup_default_session(profile_name='iconwater')

ec2_client = boto3.client('ec2', region_name='ap-southeast-2')
ssm_client = boto3.client('ssm', region_name='ap-southeast-2')  # use region code in which you are working

sleep_duration = int(os.getenv("WaitSecondsBetweenCalls", "2"))

def send_alert(alert_data):
    topic_arn = os.getenv("TopicARN", "")

    if topic_arn == "":
        print("send_alert: Missing topic ARN. Returning without sending alert.")
        return

    subject = os.getenv('CustomerID', '') + " - Missing Trend DS Agent Check"
    message = "Missing Trend DS Agent Check Results: \n\n" + alert_data

    print("send_alert: *** Sending alert ***")
    print("send_alert: Message: {0}".format(message))

    client = boto3.client('sns')
    response = client.publish(TargetArn=topic_arn,
                              Message=message,
                              Subject=subject)

def get_instance_name(instance_id):

    instance_name = ""

    ec2 = boto3.resource('ec2')
    instances = ec2.instances.filter(Filters=[{'Name': 'instance-id', 'Values': [instance_id]}])

    #for instance in instances:
    #    print(instance.id, instance.instance_type)

    for instance in instances:
        for tag in instance.tags:
            if "Name" in tag['Key']:
                instance_name = tag['Value']

    return instance_name

def get_instances(os):

    instances = []

    # Check running or stopped instances
    response = ec2_client.describe_instances(
        Filters=[
            {
                'Name': 'instance-state-name',
                'Values': ['running']
            }
        ])

    # Iterate over instance(s)
    for r in response['Reservations']:
        for inst in r['Instances']:
            inst_id = inst['InstanceId']
            tags = inst['Tags']

            ins_tag = ""

            for tag in tags:
                if "OSFamily" in tag['Key']:
                    ins_tag = (tag['Value'])
                    break
                else:
                    ins_tag = "NA"

            if ins_tag == os:
                instances.append(inst_id)

    return instances

def ssm_run_command(instance_id, cmd, os_family):

    document = "AWS-RunPowerShellScript"

    if (os_family == "Linux"):
        document = "AWS-RunShellScript"

    response = ssm_client.send_command(
        InstanceIds=[
            instance_id  # use instance id on which you want to execute, even multiple is allowed
        ],
        DocumentName=document,
        Parameters={
            'commands': [
                cmd
            ]
        },
    )

    #print(response)

    sleep(sleep_duration)  # Seconds to wait for command to execute

    command_id = response['Command']['CommandId']
    output = ssm_client.get_command_invocation(CommandId = command_id, InstanceId = instance_id)

    return output['StandardOutputContent']

def check_trend_agent_windows():

    os_family = "Windows"

    instances = get_instances(os_family)
    command = "$svc = Get-Service 'ds_agent' -ErrorAction SilentlyContinue;$svc.Status "

    instances_with_wrong_trend_status = []

    for instance in instances:
        print("Checking instance: " + instance)
        agent_status = ssm_run_command(instance, command, os_family)

        if ( agent_status[0:7] != "Running"):
            instances_with_wrong_trend_status.append(instance)

    result_str = ""

    if (len(instances_with_wrong_trend_status) > 0):

        result_str = "Following " + os_family + " instances have missing or stopped Trend DS Agent:\n\n"

        for instance in instances_with_wrong_trend_status:
            result_str = result_str + get_instance_name(instance) + " (" + instance + ")\n\n"

    return result_str

def check_trend_agent_linux():
    os_family = "Linux"

    instances = get_instances(os_family)
    command = 'service ds_agent status | grep running | wc -l'

    instances_with_wrong_trend_status = []

    for instance in instances:
        print("Checking instance: " + instance)
        agent_status = ssm_run_command(instance, command, os_family)

        if (agent_status[0:1] != "1"):
            instances_with_wrong_trend_status.append(instance)

    result_str = ""

    if (len(instances_with_wrong_trend_status) > 0):

        result_str = "Following " + os_family + " instances have missing or stopped Trend DS Agent:\n\n"

        for instance in instances_with_wrong_trend_status:
            result_str = result_str + get_instance_name(instance) + " (" + instance + ")\n\n"

    return result_str

def lambda_handler(event, context):

    result_lin = check_trend_agent_linux()
    result_win = check_trend_agent_windows()

    if result_lin != "" or result_win != "":
        result = result_lin + "\n\n" + result_win
        print(result)
        send_alert(result)

if __name__ == "__main__":
    lambda_handler(0, 0)
