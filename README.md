                 █▀█                  
              ▄▄▄▀█▀            
              █▄█ █    █▀█        
           █▀█ █  █ ▄▄▄▀█▀      
        ▄▄▄▀█▀ █  █ █▄█ █ ▄▄▄       
        █▄█ █  █  █  █  █ █▄█        ███╗   ██╗ █████╗ ██████╗ ████████╗██╗  ██╗ █████╗ 
     ▄▄▄ █  █  █  █  █  █  █ ▄▄▄     ████╗  ██║██╔══██╗██╔══██╗╚══██╔══╝██║  ██║██╔══██╗
     █▄█ █  █  █  █▄█▀  █  █ █▄█     ██╔██╗ ██║███████║██████╔╝   ██║   ███████║███████║
      █  █   ▀█▀  █▀▀  ▄█  █  █      ██║╚██╗██║██╔══██║██╔═══╝    ██║   ██╔══██║██╔══██║
      █  ▀█▄  ▀█▄ █ ▄█▀▀ ▄█▀  █      ██║ ╚████║██║  ██║██║        ██║   ██║  ██║██║  ██║
       ▀█▄ ▀▀█  █ █ █ ▄██▀ ▄█▀       ╚═╝  ╚═══╝╚═╝  ╚═╝╚═╝        ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝
         ▀█▄ █  █ █ █ █  ▄█▀                         Decentralized Multi-Agent Workflows
            ▀█  █ █ █ █ ▌▀                                                 www.naptha.ai
              ▀▀█ █ ██▀▀                                                    

 
# Naptha Python SDK

Naptha enables users to build decentralized multi-agent workflows. Decentralized workflows can run on one or more nodes (rather than on one central server), with different LLMs, and with many local data sources, opening up new use cases for AI devs. 

Here's Yohei (creator of BabyAGI) admitting that [BabyAGI isn't a true multi-agent system](https://x.com/yoheinakajima/status/1781183534998380576) since the agents use the same LLM and code base. You can watch a demo video where we run BabyAGI as a true multi-agent system [here](https://www.youtube.com/watch?v=nzV04zOA0f0).

<img src="images/multi-node-flow.png" width="100%">

## Pre-requisites

Install Python [Poetry](https://python-poetry.org/docs/):

```bash
pipx install poetry
```

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

Choose whether you want to interact with a local Naptha node or a hosted Naptha node. For a local node, set ```NODE_URL=http://localhost:7001``` in the .env file. To use a hosted node, set ```NODE_URL=http://node.naptha.ai:7001``` or ```NODE_URL=http://node1.naptha.ai:7001```.

## Get Started

## Sign Up

You can sign up for an account on the Naptha Hub (and generate a public/private keypair) using the commandline tool:

```bash
naptha signup
```

## Nodes

### Explore Nodes on the Network

You can use the CLI to see a list of available nodes:

```bash
naptha nodes
```

Make note of a Node ID for running a workflow below.

### Check out available Agents

Agents can be workflows, agents or multi-agent systems. Agents typically involve one or more LLMs, along with humans in the loop. You can also use the CLI to explore available agents that you can run on a node:

```bash
naptha agents
```

For each agent, you will see a url where you can check out the code.

### Create a New Agent

```bash
naptha agents agent_name -p "description='Agent description' url='ipfs://QmNer9SRKmJPv4Ae3vdVYo6eFjPcyJ8uZ2rRSYd3koT6jg' type='package' version='0.1'" 
```

### Delete a Agent

```bash
naptha agents -d agent_name
```

### Run an Agent

Now you've found a node and a agent you'd like to run, so let's run it locally! You can use the commandline tool to connect with the node and run the workflow. 

```bash
# usage: naptha run <agent_name> <agent args>
naptha run hello_world_agent -p "firstname=sam surname=altman"
```

Try an agent that uses the local LLM running on your node:

```bash
naptha run simple_chat_agent -p "prompt='what is an ai agent?'"
```

You can also run agents from docker images:

```bash
naptha run docker_hello_world -f ./example_yamls/docker_hello_world.yml
```

### Run Multi-Agent Networks across several Nodes

```bash
naptha run multiagent_chat -p "prompt='i would like to count up to ten, one number at a time. ill start. one.'" --worker_nodes "http://node.naptha.ai:7001,http://node1.naptha.ai:7001"
```

```bash
naptha run babyagi -p "objective='Research the history of football'" --worker_nodes "http://node.naptha.ai:7001,http://node1.naptha.ai:7001"
```

```bash
naptha run multiagent_debate -p "initial_claim='Teslas price will exceed $250 in 2 weeks.' max_rounds=2 context='Teslas current price is $207, and recent innovations and strong Q2 results will drive the price up.

News Summary 1:
Tesla stock was lower to start a new week of trading, falling as investors worry about global growth. Shares of the electric-vehicle giant were down 7.3% in premarket trading Monday at $192.33. Stocks around the world were falling as investors fretted that weak economic data signal a recession ahead. Despite positive comments from CEO Elon Musk about Tesla’s sales, the stock has fallen about 16% this year and is struggling to overcome negative global investor sentiment.

News Summary 2:
Tesla faces growing competition and softening demand, impacting its stock price which is trading 43% below its all-time high. The company’s profitability is declining, with earnings per share shrinking 46% year-over-year in Q2 2024. Despite recent price cuts and a plan to produce a low-cost EV model, sales growth has decelerated. Tesla is also involved in autonomous self-driving software, humanoid robots, and solar energy, but these segments may take years to significantly impact revenue.
'" --worker_nodes "http://node.naptha.ai:7001"
```

### Interact with Node Storage

After the agent runs finish, you can download the file from the node using:

```bash
naptha read_storage -id <agent_run_id>
```

You can write to the node using:

```bash
naptha write_storage -i files/<filename>.jpg
```

### Interact with IPFS thorugh Node
```bash
naptha write_storage -i files/<filename>.jpg --ipfs
```

## Using the SDK non-interactively

To use the SDK as part of a script, start with importing the hub and service subcomponents.
```python
import asyncio
from naptha_sdk.client.naptha import Naptha
from naptha_sdk.client.node import Node
from naptha_sdk.task import Task as Agent
from naptha_sdk.flow import Flow
from naptha_sdk.user import generate_user
import os
```


```python
async def main():
   naptha = Naptha(
      hub_url="ws://node.naptha.ai:3001/rpc",
      node_url="http://node.naptha.ai:7001",
      public_key=get_public_key(os.getenv("PRIVATE_KEY")),
      hub_username=os.getenv("HUB_USER"), 
      hub_password=os.getenv("HUB_PASS"), 
   )

   async with naptha as naptha:
         await naptha.hub.signin(hub_username, hub_password) 

  flow_inputs = {"prompt": 'i would like to count up to ten, one number at a time. ill start. one.'}
  worker_nodes = [Node("http://node.naptha.ai:7001"), Node("http://node1.naptha.ai:7001")]

  agentnet = Flow(name="multiplayer_chat", user_id=naptha.user["id"], worker_nodes=worker_nodes, agent_run_params=flow_inputs)

  agent1 = Agent(name="chat_initiator", fn="simple_chat_agent", worker_node=worker_nodes[0], orchestrator_node=naptha.node, flow_run=agentnet.flow_run)
  agent2 = Agent(name="chat_receiver", fn="simple_chat_agent", worker_node=worker_nodes[1], orchestrator_node=naptha.node, flow_run=agentnet.flow_run)

  response = await agent1(prompt=flow_inputs["prompt"])

  for i in range(10):
      response = await agent2(prompt=response)
      response = await agent1(prompt=response)

asyncio.run(await main())

```

# ***More examples and tutorials coming soon.***

### Create your own Agent

Clone the [base template](https://huggingface.co/NapthaAI/template) for creating agent and flow agents, and follow the instructions in the readme for prototyping the agent. You can check out other examples of agents and networks at https://huggingface.co/NapthaAI.

Register your agent on the Naptha Hub (Coming Soon).

# Run a Node

You can run your own Naptha node, and earn rewards for running workflows. Follow the instructions at https://github.com/NapthaAI/node


# Community

### Links

* Check out our [Website](https://www.naptha.ai/)  
* Contribute to our [GitHub](https://github.com/NapthaAI)
* Request to join the Naptha community on [HuggingFace](https://huggingface.co/NapthaAI)
* Follow us on [Twitter](https://twitter.com/NapthaAI) and [Farcaster](https://warpcast.com/naptha)  
* Subscribe to our [YouTube](https://www.youtube.com/channel/UCoDwQ3DZa1bRJPrIz_4_02w)

### Bounties and Microgrants

Have an idea for a cool use case to build with our SDK? Get in touch at team@naptha.ai.