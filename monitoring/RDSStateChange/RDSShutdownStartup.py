from __future__ import print_function
import boto3
from datetime import datetime, timedelta

prof_name = "vicroads"
acc_number = "862017364710"

#prof_name = "default"
#acc_number = "077617143265"

#boto3.setup_default_session(profile_name=prof_name)

def rds_start(list_instances):

    for instance in list_instances:
        this_inst = instance.split(",")
        db_instance_id = this_inst[0]
        environment = this_inst[1]
        print ("{0} (UTC): Starting Instance '{1}' from Environment '{2}'".format(datetime.utcnow(), db_instance_id, environment))
        boto3.client('rds').start_db_instance(DBInstanceIdentifier=db_instance_id)

def rds_stop(list_instances):

    for instance in list_instances:
        this_inst = instance.split(",")
        db_instance_id = this_inst[0]
        environment = this_inst[1]
        print("{0} (UTC): Stopping Instance '{1}' from Environment '{2}'".format(datetime.utcnow(), this_inst[0], this_inst[1]))
        boto3.client('rds').stop_db_instance(DBInstanceIdentifier=db_instance_id)

def lambda_handler(event, context):

    rds = boto3.client('rds')

    instances_to_start = []
    instances_to_stop = []

    # Date calculation
    date = datetime.utcnow() + timedelta(hours=10)

    current_hour = date.hour
    current_day = date.weekday()

    #print("current_hour: " + str(current_hour))
    #print("current_day: " + str(current_day))

    # return 0
    #
    # if (current_hour > 23):
    #     current_hour = current_hour - 24
    #     current_day = current_day + 1
    #
    # if (current_day == 0):
    #     current_day = 6
    # else:
    #     current_day = current_day - 1
    #
    # print("current_hour: " + str(current_hour))
    # print("current_day: " + str(current_day))
    #
    # return 0

    print("Running State Change Script for hour {0} on day {1}".format(current_hour, current_day))

    try:
        # get all of the db instances
        dbs = rds.describe_db_instances()

        for db in dbs['DBInstances']:
            #print("--------------------------------------------")
            print("Checking RDS Instance: {0} {1} {2} {3} {4}".format(db['DBInstanceIdentifier'], db['MasterUsername'], db['Endpoint']['Address'], db['Endpoint']['Port'], db['DBInstanceStatus']) )

            # arn:aws:rds:ap-southeast-2:862017364710:db:sr178x5y9usse6o
            arn = "arn:aws:rds:ap-southeast-2:" + acc_number + ":db:" + db['DBInstanceIdentifier']
            # print("{0}".format(arn))

            tags = rds.list_tags_for_resource(ResourceName=arn)
            # print (tags)

            instance_id = db['DBInstanceIdentifier']
            current_status = db['DBInstanceStatus']
            environment = ""
            startup = ""
            shutdown = ""

            for tg in tags['TagList']:

                if tg['Key'] == 'Environment':
                    environment = tg['Value']

                if tg['Key'] == 'StartUp':
                    startup = tg['Value']

                if tg['Key'] == 'Shutdown':
                    shutdown = tg['Value']

            if environment == "PROD": # Skip prod
                if startup != "":
                    print("Skipping Production RDS Instance. Do not assign StartUp/Shutdown Tags to PROD instances.")

                if shutdown != "":
                    print("Skipping Production RDS Instance. Do not assign StartUp/Shutdown Tags to PROD instances.")

                continue

            if startup != "":
                startup_schedule =  startup.split(" ")
                print("StartUp:  {0}".format(startup_schedule))
                if (int(startup_schedule[current_day]) == current_hour):
                    if current_status == "stopped" : instances_to_start.append(instance_id + "," + environment)

            if shutdown != "":
                shutdown_schedule =  shutdown.split(" ")
                print("Shutdown: {0}".format(shutdown_schedule))
                if (int(shutdown_schedule[current_day]) == current_hour):
                    if current_status == "available": instances_to_stop.append(instance_id + "," + environment)

            #print("--------------------------------------------")

        #For testing
        # instances_to_stop.append("1-asdasdsadadssad,STG")

        if (len(instances_to_start) == 0): print ("{0} (UTC): No instances to start at this time.".format(datetime.utcnow()))
        if (len(instances_to_stop) == 0): print ("{0} (UTC): No instances to stop at this time.".format(datetime.utcnow()))

        rds_start(instances_to_start)
        rds_stop(instances_to_stop)

    except Exception as error:
        print(error)

lambda_handler(0, 0)
