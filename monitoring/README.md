# Introduction
Monitoring scripts written in Python, to be deployed as Lambda functions in AWS environment.

1.	check-missing-metrics:
Script to query for Cloudwatch metrics for all running EC2 instance and if unavailable send a message through an SNS topic to check for EC2Config service
2.	Check_Open_RDP_Ports:
Script to query for EC2 Instances that have security group with specific port allowed. Currently we require it to check RDP port being open.
3.	kms-check-idle-and-workspace-users:
Script to check users who have not logged in to AWS console or Workspaces.
4.	kms-ec2-timezone-check-tool:
Script to check timezone on EC2 instance. Uses SSM service.
5.	kms-logs-agent-check-tool:
Script to check logs agent is installed on EC2 instance. Uses SSM service.
6.	kms-mandatory-tags-check-tool:
Script to check mandatory tags applied to resources on EC2 instance.
7.	kms-mandatory-workspaces-tags-check-tool:
Script to check mandatory tags applied to resources on Workspaces.
8.	kms-missing-ssm-instances:
Script to check SSM agent is installed on EC2 instances.
9.	kms-s3-inspector-check-public-buckets:
Script to check Public buckets.
10.	kms-site247-agent-check-tool:
Script to check Siet24x7 agent is installed on EC2 instances.
11.	kms-snapshot-check-tool:
Script to check new snapshots are created of EC2 instances under management.
12.	kms-trend-agent-check-tool:
Script to check Trend AntiMalware agent is installed on EC2 instances.
13.	Lamda_Alarm_Creation_SSVC:
Script to create alarms for EC2 instances.
14.	MonitorSubnets:
Script to monitor subnets for IP exhaustion.
15.	RDSStateChange:
Script to shutdown RDS instances at specified time.
