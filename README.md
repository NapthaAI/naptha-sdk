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

```
naptha tasks
```

### Browse existing RFPs

You can browse all RFPs using:

```
naptha rfps
```

## Nodes

### Explore Nodes on the Network

You can use the CLI to see a list of available nodes:

```
naptha nodes
```

Make note of a Node ID for running a workflow below.

### Check out available Modules

Modules can be workflows, agents or multi-agent systems. Modules typically involve one or more LLMs, along with humans in the loop. You can also use the CLI to explore available modules that you can run on nodes:

```
naptha modules
```

### Get Credits (Nevermined app currently not working)

Log in and subscribe to Naptha's [Free Subscription](https://testing.nevermined.app/en/subscription/did:nv:bcc485bc7155a50d13ba425a3b8bbd30eea8e4c90ecfeadfedf5cdd702e3c793) tier on the Nevermined app.

You can check your credits using:

```
naptha credits
```

### Run a Module

Now you've found a node and a workflow you'd like to run, so let's run it! You can use the commandline tool to connect with the node and run the workflow (replace the node ID with a real node ID found on the Hub).

```
# usage: naptha run <module_id> <module args>
naptha run chat --prompt "tell me a joke" 
```

### Create your own Module

(Coming Soon)

# Run a Node

You can run your own Naptha node, and earn rewards for running workflows. Follow the instructions at https://github.com/NapthaAI/node
