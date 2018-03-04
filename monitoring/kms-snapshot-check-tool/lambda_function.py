import boto3
import os
import datetime,dateutil
from dateutil.relativedelta import relativedelta

region_list = ['ap-southeast-2']        # Describe your regions here
owner=os.getenv('OwnerId', '')          # Your owner id is necessary for your snapshots
num_days=int(os.getenv('NumDays', '3')) # How many days old snapshot to report
ask_for_snapshot = 'N'                  # Should we create snapshot if missing

def send_alert(alert_data):
    
    topic_arn = os.getenv("TopicARN", "")
    
    if topic_arn == "":
        print("send_alert: Missing topic ARN. Returning without sending alert.")
        return

    subject = os.getenv('CustomerID', '') + " - Missing Volume Snapshot Check"
    message = "Missing Volume Snapshot Check Results: \n\n" + "Where reported, old snapshot means snapshot was created more than " + str(num_days) + " days from today.\n\n" + alert_data

    print("send_alert: *** Sending alert ***")
    print("send_alert: Message: {0}".format(message))

    client = boto3.client('sns')
    response = client.publish(TargetArn=topic_arn, 
                              Message=message, 
                              Subject=subject)

#For creating snapshots
def create_snapshot(volume):
    Description='Created for volume '+volume
    client = boto3.client('ec2')
    response = client.create_snapshot(
        DryRun=False,
        VolumeId=volume,
        Description=Description
    )

def find_snapshots():
    result_str = ""
    
    client = boto3.client('ec2')
    response = client.describe_snapshots(OwnerIds=[owner])
    snapshot_list=response['Snapshots']

    #Iterate over regions
    i = 0
    for region in region_list:
        #print("\n"+"#"*60+"  "+region+"  "+"#"*60+"\n")
        client = boto3.client('ec2', region_name=region)
        #Check running or stopped instances
        response = client.describe_instances(
            Filters=[
                {
                    'Name': 'instance-state-name',
                    'Values': ['running', 'stopped']
                }
            ])
        #Iterate over instance(s)
        for r in response['Reservations']:
            for inst in r['Instances']:
                inst_id=inst['InstanceId']
                tags=inst['Tags']
                #Check the Name tag
                for tag in tags:
                    if 'Name' in tag['Key']:
                        ins_tag=(tag['Value'])
                        break
                    else:
                        ins_tag="NA"
                i = i + 1
                ii = str (i)
                if i < 10:
                    ii = "0" + str(i)
                #print(ii+") "+"-"*10+" "+ins_tag+" ("+inst_id+") "+"-"*10)
                volumes=inst['BlockDeviceMappings']
                volume_temp=[]
                #Iterate over instance's volume(s)
                for volume in volumes:
                    volume=volume['Ebs']['VolumeId']
                    volume_temp.append(volume)
                #print("Instance's volumes: ",volume_temp)
                volumes_without_snapshots=[]
                volumes_with_snapshots=[]
                recent_snapshots=[]
                old_snapshots=[]

                #Find the volumes in snapshots
                for volume in volume_temp:
                    for snapshot in snapshot_list:
                        snapshot_volume=snapshot['VolumeId']
                        #Check if volume in snapshot, if so check the date
                        if volume == snapshot_volume:
                            volumes_with_snapshots.append(volume)
                            volumes_with_snapshots=list(set(volumes_with_snapshots))
                            snapshot_date=snapshot['StartTime']
                            a = dateutil.parser.parse(datetime.datetime.now().strftime('%Y-%m-%d'))
                            b = dateutil.parser.parse(datetime.date.strftime(snapshot_date,'%Y-%m-%d'))
                            diff = relativedelta(a, b)
                            snapshot_creation=diff.years*12+diff.months*30+diff.days
                            if snapshot_creation<num_days:      #Check the snapshots older than 3 days
                                recent_snapshots.append(volume)
                                recent_snapshots=list(set(recent_snapshots))
                            else:
                                old_snapshots.append(volume)
                                old_snapshots=list(set(old_snapshots))

                            if volume in volumes_without_snapshots:
                                volumes_without_snapshots.remove(volume)
                        #Check if volume doesn't have snapshot
                        if (volume != snapshot_volume) and (volume not in volumes_with_snapshots):
                            volumes_without_snapshots.append(volume)
                            volumes_without_snapshots=list(set(volumes_without_snapshots))

                    removed_recent_snapshots=list(set(old_snapshots)-set(recent_snapshots))

                if len(removed_recent_snapshots)>0:
                    #print("Volumes with old snapshots: ",removed_recent_snapshots)
                    str1 = "Volumes with old snapshots: {0} for Instance: {1} ({2})\n\n"
                    str2 = str1.format(removed_recent_snapshots,ins_tag,inst_id)
                    #print(str_temp)
                    result_str = result_str + " " + str2
                    
                    
                if len(volumes_without_snapshots)>0:
                    #print("Volumes without snapshots: ",volumes_without_snapshots)
                    str1 = "Volumes without snapshots: {0} for Instance: {1} ({2})\n\n"
                    str2 = str1.format(volumes_without_snapshots,ins_tag,inst_id)
                    #print(str_temp)
                    result_str = result_str + " " + str2
                    
                #print("\n")
                #ask for creating snapshot
                #if len(volumes_without_snapshots)>0 or len(removed_recent_snapshots)>0:
                #    ask_for_snapshot = input("Do you want to create snapshot of the volumes?: Y/n ")
                if ask_for_snapshot in ['Y','y']:
                    for volume in removed_recent_snapshots:
                        print("Creating snapshot for volume: ",volume)
                        create_snapshot(volume)
                    for volume in volumes_without_snapshots:
                        print("Creating snapshot for volume: ",volume)
                        create_snapshot(volume)
    return result_str
#if __name__ == "__main__":
def lambda_handler(event, context):
    try:
        result_str = find_snapshots()
        if result_str: # not empty
            send_alert(result_str)
        return 0
    except Exception as err:
        print(err)
        return 1
