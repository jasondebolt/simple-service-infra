#!/bin/bash

set -e

# Validates all infrastructure templates.${DIR}/
templates=$(find . -name '*template*.yaml' -not -path '*/\.*')

export TERM=xterm-color
red() { tput setaf 1; echo $1; tput sgr0; }
blue() { tput setaf 6; echo $1; tput sgr0; }
green() { tput setaf 2; echo $1; tput sgr0; }

# Display all files beforehand for convenience.
for template in $templates; do
    blue "validating $template"
done

echo "Starting validation..."

for template in $templates; do
  blue "validating $template"
  # Use fileb:// here since CodeBuild sometimes cannot validate using file://
  aws cloudformation validate-template --template-body file://$template 1> /dev/null
done

green "All templates are valid!"
