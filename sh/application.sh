#!/bin/bash

# if you're on OS X use brew or pip to install awscli
# if you're on Linux use pip
# on Windows you can instal Python and pip or install Virtualbox / VMWare Fusion

# aws profiles are good. You can have one for the prod account and one for the dev account
# run aws credentials to get started

# you must include CAPABILITY_NAMED_IAM for the InstanceProfile used in the Elastic Beanstalk stack

CUSTOMER=DE #This has been abbreviated to reduce chance of resources exceeding 20 char limit
ENVIRONMENT=SIT #Also using the same value for PlatformParameter
#PROFILE="${CUSTOMER}-${ENVIRONMENT}"
PROFILE=default #This is a local reference to your AWS profile see https://docs.aws.amazon.com/cli/latest/userguide/cli-multiple-profiles.html for information
ACCOUNTID=`aws --profile ${PROFILE} sts get-caller-identity | jq '.Account' | sed 's/\"//g'`
REGION=ap-southeast-2
BASEAMI=ami-16b48075
S3Bucket=${ACCOUNTID}-cloudformation
# end of configurables

FILENAME=`basename "$0"`
STACKNAME=${CUSTOMER}-${ENVIRONMENT}
APPLICATION_CONFIG_FILE=${ENVIRONMENT}.json
if [ -z $1 ]
then
  OPERATION=create
else
  OPERATION=$1
fi

if [ $OPERATION == create ]; then
   aws --profile ${PROFILE} \
  --region ${REGION} \
  cloudformation $OPERATION-stack \
  --stack-name ${STACKNAME} \
  --parameters ParameterKey=PlatformParameter,ParameterValue=${ENVIRONMENT} \
ParameterKey=BaseAMI,ParameterValue=${BASEAMI} \
  --template-url https://s3-ap-southeast-2.amazonaws.com/${ACCOUNTID}-cloudformation/${ENVIRONMENT}/cloudFormation/000-Platform.template \
  --capabilities CAPABILITY_NAMED_IAM;
fi

if [ $OPERATION == update ]; then
  aws --profile ${PROFILE} \
  --region ${REGION} \
  cloudformation $OPERATION-stack \
  --stack-name ${STACKNAME} \
  --parameters ParameterKey=PlatformParameter,UsePreviousValue=true \
ParameterKey=BaseAMI,UsePreviousValue=true \
  --template-url https://s3-ap-southeast-2.amazonaws.com/${ACCOUNTID}-cloudformation/${ENVIRONMENT}/cloudFormation/000-Platform.template \
  --capabilities CAPABILITY_NAMED_IAM;
fi

if [ $OPERATION == delete ]; then
  aws --profile ${PROFILE} --region ${REGION} cloudformation delete-stack --stack-name ${STACKNAME}
fi

if [ $OPERATION == sync ]; then
  aws s3 sync --exclude "*" --include "*.json" --include "*.template" s3://${S3Bucket}/${ENVIRONMENT}/ s3://${S3Bucket}/${ENVIRONMENT}/backup/ --profile ${PROFILE}
  aws s3 sync --exclude "*" --include "*.json" --include "*.template" ./cloudformation/ s3://${S3Bucket}/${ENVIRONMENT}/ --profile ${PROFILE}
fi
