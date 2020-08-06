"""Makes GitHub API calls from CodeBuild jobs.

This script is called at the end of CodeBuild jobs to do the following:
    1) Report CodeBuild job status to GitHub Statuses API for a given pull request.
    2) Report URL of deployed ECS cluster to GitHub comments API for a given pull request.

USAGE EXAMPLES:
      pull_request.py statuses BaseDockerImages pending "Builds Base Docker Images" codebuild_url
      pull_request.py statuses BaseDockerImages pending "Builds Base Docker Images" "https://..."
"""

__author__ = "Jason DeBolt (deboltjd@amazon.com)"

import os
import urllib
from urllib.parse import quote
import sys
import copy
import json
import requests
import boto3

# Boto clients
ssm_client = boto3.client('ssm')

# These env variables are passed in via CloudFormation
ENV_VARS_MAP = {
  'dash_case_project_name': os.environ.get('DASH_CASE_PROJECT_NAME'),
  'github_organization': os.environ.get('GITHUB_ORGANIZATION'),
  'environment_name': os.environ.get('ENVIRONMENT_NAME'),
  'namespace_name': os.environ.get('NAMESPACE_NAME'),
  'github_repo': os.environ.get('GITHUB_REPO'),
  'infra_branch': os.environ.get('GIT_BRANCH'),
  'source_branch': os.environ.get('SOURCE_BRANCH'),
  'github_token_ssm_path': os.environ.get('GITHUB_TOKEN_SSM_PATH'),
  'pull_request_number': os.environ.get('PULL_REQUEST_NUMBER'),
  'pull_request_domain': os.environ.get('PULL_REQUEST_DOMAIN')
}

# These env variables are always avaialable in AWS CodeBuild
CODEBUILD_BUILD_ARN = os.environ.get('CODEBUILD_BUILD_ARN')
CODE_BUILD_REGION = os.environ.get('AWS_DEFAULT_REGION')
CODEBUILD_BUILD_SUCCEEDING = int(os.environ.get('CODEBUILD_BUILD_SUCCEEDING', 0))
CODEBUILD_RESOLVED_SOURCE_VERSION = os.environ.get('CODEBUILD_RESOLVED_SOURCE_VERSION')
APP_COMMIT = os.environ.get('APP_COMMIT')
CODEBUILD_BUILD_ID = os.environ.get('CODEBUILD_BUILD_ID')
CODEBUILD_PROJECT_NAME = CODEBUILD_BUILD_ID.split(':')[0]
PIPELINE_NAME = os.environ.get('CODEBUILD_INITIATOR', '/').split('/')[1]

VARS_MAP = copy.deepcopy(ENV_VARS_MAP)
if '-infra-pipeline-pr-' in PIPELINE_NAME:
    # The environment variables are not present or needed in infrastructure pipelines.
    del VARS_MAP['environment_name']
    del VARS_MAP['namespace_name']
elif '{0}-pipeline-pr-'.format(os.environ.get('DASH_CASE_PROJECT_NAME')) in PIPELINE_NAME:
    VARS_MAP = copy.deepcopy(ENV_VARS_MAP)

# GitHub vars
GITHUB_API_URL = 'https://api.github.com'

def get_ssm_value(ssm_path):
    print('getting ssm value at {0}'.format(ssm_path))
    response = ssm_client.get_parameter(Name=ssm_path, WithDecryption=False)
    return response['Parameter']['Value']

def get_code_build_url():
    return (
        'https://console.aws.amazon.com/codebuild/home?region={region}'
        '#/builds/{codebuild_build_id}/view/new').format(
            region=CODE_BUILD_REGION, codebuild_build_id=CODEBUILD_BUILD_ID)

def get_ecs_logs_url(ecs_service='web'):
    """Generates a URL to ECS stdout logs for a single ECS service.

    Only for pull requests.

    service_name: String name suffix of the ECS service name after the PR number.
    """
    dash_case_project_name=VARS_MAP['dash_case_project_name']
    environment_name=VARS_MAP['environment_name']
    namespace_name=VARS_MAP['namespace_name']
    infra_branch=VARS_MAP['infra_branch']
    pull_request_number=VARS_MAP['pull_request_number']

    cluster_name = '{dash_case_project_name}-infra-{environment_name}-{namespace_name}-{infra_branch}'.format(**locals())
    service_name = '{dash_case_project_name}-{namespace_name}-pr-{pull_request_number}-{ecs_service}'.format(**locals())
    return (
        'https://console.aws.amazon.com/ecs/home?region={region}'
        '#/clusters/{cluster_name}/services/{service_name}/logs').format(
            region=CODE_BUILD_REGION, cluster_name=cluster_name, service_name=service_name)


def send_status(context, state, description, target_url):
    # Use the App commit if it exists, otherwise the infrastructure repo commit.
    commit = APP_COMMIT or CODEBUILD_RESOLVED_SOURCE_VERSION

    if target_url == 'codebuild_url':
        target_url = get_code_build_url()
    elif target_url == 'ecs_url':
        target_url = 'https://{source_version}.{namespace_name}.{domain}'.format(
            source_version=APP_COMMIT,
            namespace_name=VARS_MAP['namespace_name'],
            domain=VARS_MAP['pull_request_domain'])
    elif target_url == 'demo_url':
        service = 'web'
        target_url = 'https://{service}-pr-{pull_request_number}.{namespace_name}.{domain}'.format(
            service=service,
            pull_request_number=VARS_MAP['pull_request_number'],
            namespace_name=VARS_MAP['namespace_name'],
            domain=VARS_MAP['pull_request_domain'])
    elif target_url == 'ecs_web_logs_url':
        target_url = get_ecs_logs_url()

    url = os.path.join(
        GITHUB_API_URL, 'repos/{0}/{1}/statuses/{2}'.format(
            VARS_MAP['github_organization'],
            VARS_MAP['github_repo'],
            commit))
    payload = {
        'context': context,
        'state': state,
        'description': description,
    }
    if target_url is not None:
        payload['target_url'] = target_url

    github_token = get_ssm_value(VARS_MAP['github_token_ssm_path'])
    headers = {'Authorization': 'token {0}'.format(github_token)}
    response = requests.post(url, data=json.dumps(payload), headers=headers)
    print(response)
    print(json.dumps(response.json(), indent=2))


def check_environment_variables():
    # All environment variables must be present to continue.
    print(json.dumps(VARS_MAP, indent=2))
    if any([val is None for val in VARS_MAP.values()]):
        print('Not all environment variables have been set. This may not '
              'be a pull-request build.')
        sys.exit(0)
    else:
        print('All environment variables are present.')


if __name__ == '__main__':
    check_environment_variables()

    github_api = sys.argv[1]

    if github_api == 'statuses': # https://developer.github.com/v3/repos/statuses/
        kwargs = {
          'context': sys.argv[2],  # This name appears on the status itself.
          'state': sys.argv[3], # either 'error', 'failure', 'pending', or 'completed'
          'description': sys.argv[4],
          'target_url': sys.argv[5] # The URL that the status links to.
        }
        if CODEBUILD_BUILD_SUCCEEDING:
            kwargs['state'] = 'success'
        else:
            kwargs['state'] = 'failure'
        send_status(**kwargs)
    else:
        print(sys.argv)
        raise Exception('Unknown GitHub API resource name provided!')
