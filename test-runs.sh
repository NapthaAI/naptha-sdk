#!/bin/bash

# Use awk to extract id value
NODE_ID=$(naptha coworkers | awk -F"'id': '" '{print $2}' | awk -F"'" '{print $1}')

if [ -z "$NODE_ID" ]; then
    echo "Failed to get node ID from 'naptha coworkers'"
    exit 1
fi

# Execute daimon template job
MODULE_NAME="hello_world_daimon_template"
YAML_FILE_PATH="./example_yamls/hello_world_daimon_template.yml"

echo "Using Node ID: $NODE_ID"
echo "Module Name: $MODULE_NAME"
echo "YAML File Path: $YAML_FILE_PATH"

# Construct and run the command
COMMAND="naptha run $NODE_ID $MODULE_NAME -f $YAML_FILE_PATH"
echo "Running command: $COMMAND"
eval $COMMAND

# Execute HF template job
MODULE_NAME="chat_coop"
PROMPT="What is the name of the architecture that is powering you?"

echo "Using Node ID: $NODE_ID"
echo "Module Name: $MODULE_NAME"
echo "Prompt: $PROMPT"

# Construct and run the command
COMMAND="naptha run $NODE_ID $MODULE_NAME -p \"$PROMPT\""
echo "Running command: $COMMAND"
eval $COMMAND

# Execute docker job
MODULE_NAME="docker_hello_world"
YAML_FILE_PATH="./example_yamls/docker_hello_world.yml"

echo "Using Node ID: $NODE_ID"
echo "Module Name: $MODULE_NAME"
echo "YAML File Path: $YAML_FILE_PATH"

# Construct and run the command
COMMAND="naptha run $NODE_ID $MODULE_NAME -f $YAML_FILE_PATH"
echo "Running command: $COMMAND"
eval $COMMAND

# Execute docker job with output dir
MODULE_NAME="docker_cv2_image"
YAML_FILE_PATH="./example_yamls/docker_cv2_image.yml"

echo "Using Node ID: $NODE_ID"
echo "Module Name: $MODULE_NAME"
echo "YAML File Path: $YAML_FILE_PATH"

# Construct and run the command
COMMAND="naptha run $NODE_ID $MODULE_NAME -f $YAML_FILE_PATH"
echo "Running command: $COMMAND"
eval $COMMAND