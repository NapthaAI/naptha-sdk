                       ▄█▀█                  
                       ▀███▀                 
                        ██▌                  
                   █▀█▄ ██▌                  
                  ▐█▄█▀ ██▌     ▄█▀█         
               ▄▄▄ ▐██  ██▌     ▀█▄█▀        
              █▄▄█ ▐██  ██▌ ▄▄▄  ██▌         
          ▄▄▄  ██▌ ▐██  ██▌▐█▄▐█ ██▌  ▄▄     
         ▐█ █▌ ██  ▐██  ██▌ ▐██  ██▌ █▄▐█    
          ███  ██  ▐██  ██▌ ▐██  ██▌ ▐██     
          ██▌  ██  ▐██  ██▌ ▐██  ██▌  ██     
      ▄▄  ██▌  ██  ▐██  ██▌ ▐██  ██▌  ██  ▄▄ 
     █▌ █▌██▌  ██  ▐██  ██▌ ▐██  ██▌  ██ █▌▐█
      ██▌ ██▌  ██   ██  ██▌▄██▀  ██▌  ██  ██▌
      ██▌ ███  ▀███  ▀  ████▀▀ ▄███  ▐██  ██▌
      ██▌  ▀██▄  ▀███▄  ██▌  ▄██▀▀ ▄███▀  ██▌    ███╗   ██╗ █████╗ ██████╗ ████████╗██╗  ██╗ █████╗ 
       ▀██▄  ▀███  ▐██  ██▌ ▐██  ▄███▀ ▄███▀     ████╗  ██║██╔══██╗██╔══██╗╚══██╔══╝██║  ██║██╔══██╗
         ▀██▄  ██  ▐██  ██▌ ▐██  ██▌  ███▀       ██╔██╗ ██║███████║██████╔╝   ██║   ███████║███████║
          ▐██  ██  ▐██  ██▌ ▐██  ██▌  ██         ██║╚██╗██║██╔══██║██╔═══╝    ██║   ██╔══██║██╔══██║
          ▐██  ██  ▐██  ██▌ ▐██  ██▌  ██         ██║ ╚████║██║  ██║██║        ██║   ██║  ██║██║  ██║
            ▀  ██  ▐██  ██▌ ▐██  ██▌  ▀          ╚═╝  ╚═══╝╚═╝  ╚═╝╚═╝        ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝
               ███▄███  ██▌ ▐██▄███▌                                Decentralized Task Orchestration
                ▀▀▀███  ██▌ ▐███▀▀                                                     www.naptha.ai

# Naptha Python SDK

Naptha helps users to solve real-world problems using AI workflows and agents. There are 3 different types of users:

1. AI Consumers define tasks related to real-world problems via the Task Marketplace.
2. Workflow Planners (likely AI developers) manage workflows and agents for rewards.
3. Platform Operators use our AI nodes to deploy and operate workflows and agents as AI services.

Decentralized workflows can run on one or more nodes (rather than on one central server) with many local data sources, opening up new use cases. 

<img src="images/autonomous-pipeline.png" width="100%">

## Install

From source:

```bash
git clone https://github.com/NapthaAI/naptha-sdk.git
cd naptha-sdk
poetry install
poetry shell
```

Create a copy of the .env file:

```bash
cp .env.example .env
```

## Get Started

## Task Marketplace

### Browse existing Tasks

You can browse all tasks using:

```bash
naptha tasks
```

### Browse existing RFPs

You can browse all RFPs using:

```bash
naptha rfps
```

## Nodes

### Explore Nodes on the Network

You can use the CLI to see a list of available nodes:

```bash
naptha nodes
```

Make note of a Node ID for running a workflow below.

### Check out available Modules

Modules can be workflows, agents or multi-agent systems. Modules typically involve one or more LLMs, along with humans in the loop. You can also use the CLI to explore available modules that you can run on a node:

```bash
naptha modules
```

For each module, you will see a url where you can check out the code. 

### Run a Module

Now you've found a node and a workflow you'd like to run, so let's run it locally! You can use the commandline tool to connect with the node and run the workflow. 

```bash
# usage: naptha run <module_id> <module args>
naptha run hello_world -p "param1=world param2=naptha" --local
```

Try a module that uses the local LLM running on your node:

```bash
naptha run chat -p "prompt='tell me a joke'" --local
```

Try a module that makes predictions about future events using:

```bash
naptha run olas_prediction -p "prompt='Will there be an initial public offering on either the Shanghai Stock Exchange or the Shenzhen Stock Exchange before 1 January 2016?'" --local
```

You can also try a module that generates images (make sure that the .env file in node has a valid Stability platform API key):

```bash
naptha run generate_image -p "prompt='Beautiful green mountains and clear blue skies. Sun shining and birds chirping. A perfect day for a hike. You are walking through the forest, enjoying the scenery, when you come across a fork in the road. Do you go left or right?'" --local
```

Now let's run an image-to-image model on this image:

```bash
naptha run image_to_image -p "prompt='Cyberpunk with a wolf' input_dir=<job_id_1>" --local
```

You can also run modules from yaml files using: 

```bash
naptha run create_profile_description -f ./example_yamls/create_profile_description.yml --local
```

Or docker images:

```bash
naptha run docker_hello_world -f ./example_yamls/docker_hello_world.yml --local
```

### Interact with Node Storage

After the jobs run, you can download the file from the node using:

```bash
naptha read_storage -id <job_id> --local
```

You can write to the node using:

```bash
naptha write_storage -i files/<filename>.jpg
```

### Get Credits

We've been interacting with a local node, so how can we interact with other nodes on the Naptha network? Log in and subscribe to Naptha's [Free Subscription](https://testing.nevermined.app/en/subscription/did:nv:bcc485bc7155a50d13ba425a3b8bbd30eea8e4c90ecfeadfedf5cdd702e3c793) tier on the Nevermined app. Select the Profile button in the top right-hand corner, and copy the address beside My Wallet. Paste this value to ```WALLET_ADDRESS``` in the ```.env``` file. You can now check your credits using:

```bash
naptha credits
```

You can list available compute node services using:

```bash
naptha services
```

## Using the SDK non-interactively
To use the SDK as part of a script, start with importing the hub and service subcomponents.
```python
from naptha_sdk.hub import Hub
from naptha_sdk.services import Services
```

You'll also want to set the necessary environmental variables before running the rest of your script. One simple way to do this is like so:

```python
from dotenv import load_dotenv

load_dotenv()
```

Decentralized agent workflows are necessarily asynchronous. We'll need a library to handle async updates:

```python
import asyncio
```

Now that we've imported the necessary components, we can easily define functions to assist in orchestration.

A function to list tasks could look like this:

```python
async def list_tasks(hub):
    tasks = await hub.list_tasks()
    for task in tasks:
        print(task)
```

# ***More examples and tutorials coming soon.***

### Create your own Module

(Coming Soon)

# Run a Node

You can run your own Naptha node, and earn rewards for running workflows. Follow the instructions at https://github.com/NapthaAI/node
