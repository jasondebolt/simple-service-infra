"""Helper utility for generating JSON config files from AWS CodeBuild context (Environment Variables)

Template Configuration Reference:
https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/continuous-delivery-codepipeline-action-reference.html

USAGE:
  python config_helper.py config_deps

"""

__author__ = "Jason DeBolt (deboltjd@amazon.com)"

import sys
import os
import json

PIPELINE_DEPS_TEMPLATE_PARAMETERS = {
      'AdminPrincipalArn': os.environ.get('ADMIN_PRINCIPAL_ARN'),
      'DashCaseProjectName': os.environ.get('DASH_CASE_PROJECT_NAME'),
      'Domain': os.environ.get('DOMAIN'),
      'GitCommit': os.environ.get('GIT_COMMIT'),
      'GitBranch': os.environ.get('GIT_BRANCH'),
      'GitHubOrganization': os.environ.get('GITHUB_ORGANIZATION'),
      'GitHubRepo': os.environ.get('GITHUB_REPO'),
      'GitHubTokenSSMPath': os.environ.get('GITHUB_TOKEN_SSM_PATH'),
      'GitHubWebhookSecretSSMPath': os.environ.get('GITHUB_WEBHOOK_SECRET_SSM_PATH'),
      'PipelineTemplatePath': os.environ.get('PIPELINE_TEMPLATE_PATH'),
      'TitleCaseProjectName': os.environ.get('TITLE_CASE_PROJECT_NAME')
}

PROJECTS_API_TEMPLATE_PARAMETERS = {
      'DashCaseProjectName': os.environ.get('DASH_CASE_PROJECT_NAME'),
      'GitCommit': os.environ.get('GIT_COMMIT'),
      'GitBranch': os.environ.get('GIT_BRANCH'),
      'GitHubOrganization': os.environ.get('GITHUB_ORGANIZATION'),
      'GitHubRepo': os.environ.get('GITHUB_REPO'),
      'GitHubTokenSSMPath': os.environ.get('GITHUB_TOKEN_SSM_PATH'),
      'PipelineTemplatePath': os.environ.get('PIPELINE_TEMPLATE_PATH'),
      'TitleCaseProjectName': os.environ.get('TITLE_CASE_PROJECT_NAME')
}

class JsonConfig(object):
    def __init__(self, filename, vars):
        self.filename = filename
        self.vars = vars

    def check_environment_variables(self):
        # All environment variables must be present to continue.
        all_vars_set = True
        for key, val in self.vars.items():
            if val is None:
                print('\nENVIRONMENT VARIABLE "{0}" HAS NOT BE SET!\n'.format(key))
                all_vars_set = False
        if not all_vars_set:
            # Let's fail the build by throwing an excpetion here..
            print(json.dumps(self.vars, indent=2))
            raise Exception(
                'Not all environment variables have been set. This '
                'config file cannot be created.')
        else:
            print(json.dumps(self.vars, indent=2))
            print('All environment variables are present.')

    def get_config(self):
        return self.vars

    def write_file(self):
        # Verify all environment variables at set
        self.check_environment_variables()
        filename = os.path.join(os.environ.get('CODEBUILD_SRC_DIR'), self.filename)
        config_file = open(filename, 'w')
        config_file.write(json.dumps(self.get_config(), indent=2))
        config_file.close()

class TemplateConfig(JsonConfig):
    def __init__(self, filename, vars={}, tags=None, stack_policy=None):
        JsonConfig.__init__(self, filename, vars)
        self.tags = tags
        self.stack_policy = stack_policy

    def get_config(self):
        result = {}
        if len(self.vars) > 0:
            result['Parameters'] = self.vars
        if self.tags is not None:
            result['Tags'] = self.tags
        if self.stack_policy is not None:
            result['StackPolicy'] = self.stack_policy
        return result

class DepsConfig(TemplateConfig):
    def __init__(self):
        TemplateConfig.__init__(
            self, filename='config_deps.json',
            vars=PIPELINE_DEPS_TEMPLATE_PARAMETERS)

class APIConfig(TemplateConfig):
    def __init__(self):
        TemplateConfig.__init__(
            self, filename='config_api.json',
            vars=PROJECTS_API_TEMPLATE_PARAMETERS)

def write_output_for_command(command):
    if command == 'config_deps':
        config_obj = DepsConfig()
        config_obj.write_file()
    if command == 'config_api':
        config_obj = APIConfig()
        config_obj.write_file()

if __name__ == '__main__':
    command = sys.argv[1]
    write_output_for_command(command)
