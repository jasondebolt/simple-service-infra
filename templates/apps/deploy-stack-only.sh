#!/bin/bash

# This script bypasses the app pipeline and deploys ECS services directly with a pre-existing set of tagged ECR containers.
# Use to skip long process of building a new docker image before each cloudformation deployment.
# Make sure to build all ECR images associated with given app commit before running this script.

aws cloudformation deploy \
    --stack-name ecs-delete-me \
    --template-file template-service.yaml \
    --capabilities CAPABILITY_NAMED_IAM \
    --parameter-overrides \
      DashCaseProjectName="demo1-infra" \
      Domain="fruit.deboltjd.people.a2z.com" \
      EnvironmentName="test" \
      Namespace="test" \
      InfraGitBranch="master" \
      AppGitBranch="master" \
      ImageTag="latest" \
      AppCommit="unused" \
      DesiredCount=1 \
      TaskDeregistrationDelaySeconds=0
