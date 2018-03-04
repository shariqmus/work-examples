#!/bin/bash

yum -y install zip unzip sssd wget adcli realmd krb5-workstation samba-common-tools
escd /tmp
#AWS CLI install
curl "https://s3.amazonaws.com/aws-cli/awscli-bundle.zip" -o "awscli-bundle.zip"
unzip awscli-bundle.zip
./awscli-bundle/install -i /usr/local/aws -b /usr/local/bin/aws
echo "Installed AWS CLI agent"
#Sites 24/7 install
-E bash -c "$(curl -sL https://staticdownloads.site24x7.com/server/Site24x7InstallScript.sh)" readlink -i
#AWS SSM Agent install
yum install https://s3-ap-southeast-2.amazonaws.com/amazon-ssm-ap-southeast-2/latest/linux_amd64/amazon-ssm-agent.rpm
systemctl start amazon-ssm-agent
#AWS Cloudwatch agent install
curl https://s3.amazonaws.com/aws-cloudwatch/downloads/latest/awslogs-agent-setup.py -O
sudo python ./awslogs-agent-setup.py --region ap-southeast-2
echo "Installed Cloudwatch agent version"
/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl -m ec2 -a status | jq '.version'
#Install JQ
wget -O jq https://github.com/stedolan/jq/releases/download/jq-1.5/jq-linux64
chmod +x ./jq
cp jq /usr/bin
#Set timezone to Canberra
timedatectl set-timezone Australia/Canberra
mkdir software
mount -t nfs4 -o nfsvers=4.1,rsize=1048576,wsize=1048576,hard,timeo=600,retrans=2 fs-78fe1641.efs.ap-southeast-2.amazonaws.com:/ software
