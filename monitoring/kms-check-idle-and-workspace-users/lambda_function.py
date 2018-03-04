import os
import boto3
from datetime import datetime

days = int(os.getenv('Days', '30'))
customer_id = os.getenv('CustomerID', '')
topic_arn = os.getenv('TopicARN', '')

def send_alert(output):
    if topic_arn == "":
        return

    subject = customer_id + " - User and Workspace Cleanup Audit Results"
    message = "Instructions:\n== == == == ==\n\n"
    message += "Please review the users and workspaces below for those that no longer need access to the environment.\n"
    message += "Check the company wiki for contact details to seek approval for account and disabling of the Workspace.\n"
    message += output

    client = boto3.client('sns')
    client.publish(TargetArn=topic_arn, Message=message, Subject=subject)
    print("Sent Alert")


def CheckNumGroups(client, user_name):
    i = 0

    response = client.list_groups_for_user(
        UserName=user_name
    )
    for key in response['Groups']:
        i = i + 1
        # print("Key-----", key)

    return i


def CheckNumAccessKeys(client, user_name):
    i = 0

    response = client.list_access_keys(
        UserName=user_name
    )

    for key in response['AccessKeyMetadata']:
        i = i + 1
        # print("Key-----", key)

    return i


def lambda_handler(event, context):
    output = ""

    #boto3.setup_default_session(profile_name='vicroads')

    resource = boto3.resource('iam')
    client = boto3.client("iam")

    list_a = []
    list_b = []

    list_users = client.list_users()
    # print list_users['Users'][0]['PasswordLastUsed']

    # for key in list_users:
    #    print "Key-----",key

    for this_user in list_users['Users']:
        user_name = this_user['UserName']

        password_used = ""
        new_dt = ""

        if "PasswordLastUsed" in this_user:
            password_used = this_user['PasswordLastUsed']

        if password_used != "":
            date_s = password_used
            date_s = date_s.replace(tzinfo=None)
            new_dt = datetime.utcnow() - date_s
            minutessince = int(new_dt.total_seconds() / 60)

            # output += user_name, " ", password_used, " ", new_dt, " ", minutessince)

            if (minutessince > (days * 1440)):  # 1440 min in one day
                if (CheckNumGroups(client, user_name) > 0): list_a.append("{} (Last login was on: {})".format(user_name, password_used))
        else:
            if (CheckNumAccessKeys(client, user_name) == 0): list_b.append("{} (Last login was on: Never)".format(user_name))

    output += "\n"
    output += "==========================================================\n"
    output += "Following users have not logged in for more than {} days.\n".format(days)
    output += "==========================================================\n"

    for s in list_a:
        output += s
        output += "\n\n"

    output += "\n"
    output += "==========================================================\n"
    output += "Following users have never logged in.\n"
    output += "==========================================================\n"

    for s in list_b:
        output += s
        output += "\n"

    output += "\n"

    ws = boto3.client('workspaces')

    ### calculate time diffrence
    def calculate_age(date):
        now = datetime.utcnow().date()
        then = date.date()
        age = now - then

        return age.days

    ### return Workspace UserName
    def user_name(wsid):
        items = ws.describe_workspaces()
        for item in items['Workspaces']:
            if item['WorkspaceId'] == wsid:
                return item['UserName']

    # Body
    # days = 50
    items = ws.describe_workspaces_connection_status()
    dis_num = 0
    List_Idle = []
    never_num = 0
    List_Never = []

    for item in items['WorkspacesConnectionStatus']:
        lastknown = item.get('LastKnownUserConnectionTimestamp')
        if item['ConnectionState'] == "DISCONNECTED":
            if lastknown is not None and calculate_age(lastknown) > days:
                dis_num += 1
                List_Idle.append("User name: " + user_name(item['WorkspaceId']) + " with workspace id (" + item[
                    'WorkspaceId'] + ") has been idle for " + str(calculate_age(lastknown)) + " days.")
            if lastknown is None:
                never_num += 1
                List_Never.append("User name: " + user_name(item['WorkspaceId']) + " with workspace id (" + item[
                    'WorkspaceId'] + ") has not been used yet.")

    if dis_num > 0:
        output += "==========================================================\n"
        output += "{} workspaces have been disconnected for more than {} days:\n".format(dis_num, days)
        output += "==========================================================\n"
        for i in List_Idle:
            output += "{}\n".format(i)

    if never_num > 0:
        output += "\n==========================================================\n"
        output += "{} workspaces have never been used:\n".format(never_num)
        output += "==========================================================\n"
        for j in List_Never:
            output += "{}\n".format(j)

    print(output)
    send_alert(output)

#print('Loading function')
#lambda_handler(0, 0)
