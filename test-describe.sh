#!/bin/bash

# Use awk to extract id value
NODE_ID=$(poetry run naptha coworkers | awk -F"'id': '" '{print $2}' | awk -F"'" '{print $1}')

if [ -z "$NODE_ID" ]; then
    echo "Failed to get node ID from 'naptha coworkers'"
    exit 1
fi

# Execute daimon template job
MODULE_NAME="describe_daimon_template"
YAML_FILE_PATH="./example_yamls/describe_daimon_template.yml"

echo "Using Node ID: $NODE_ID"
echo "Module Name: $MODULE_NAME"
echo "YAML File Path: $YAML_FILE_PATH"

# Construct and run the command with expect
COMMAND="poetry run naptha run $NODE_ID $MODULE_NAME -f $YAML_FILE_PATH"
echo "Running command: $COMMAND"
eval $COMMAND