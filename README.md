
             %
             %%
             %%#
             %-+%
           %%%+.#
         #%#%.*=-%#
       #%=.%+-*%-:%%
      %%#*.*.#--%--*=%
     #%*%*.*.+- +-:%*%#     ██████╗  █████╗ ██╗███╗   ███╗ ██████╗ ███╗   ██╗ 
    #@:= *.%::#+:%%.=.%#    ██╔══██╗██╔══██╗██║████╗ ████║██╔═══██╗████╗  ██║
     %%:*#.#*:*%=:*:=%%     ██║  ██║███████║██║██╔████╔██║██║   ██║██╔██╗ ██║
      %*-*:..=-%*:*:##      ██║  ██║██╔══██║██║██║╚██╔╝██║██║   ██║██║╚██╗██║
       ##+*--+-%=#+##       ██████╔╝██║  ██║██║██║ ╚═╝ ██║╚██████╔╝██║ ╚████║
        #%#+=+=%*%%#        ╚═════╝ ╚═╝  ╚═╝╚═╝╚═╝     ╚═╝ ╚═════╝ ╚═╝  ╚═══╝
          #%#%#%%#          Decentralized Compute for Agents   www.naptha.ai

# Daimon Python SDK

## Install

```
pip install daimon-sdk
```

## Get Started

### Create an Acount

Create an account on the [Hub](https://hub.naptha.ai/). You get 1000 free NPT credits when you join. 

### Explore Available Compute Nodes

Navigate to the Compute Providers page to explore available compute nodes and compare prices. 

Alternatively, you can use the CLI to see a list of available compute providers:

```
daimon auctions
```

### Check out existing AI Modules

Navigate to the AI Modules page to explore available AI modules to run on your compute node.

```
daimon modules
```

### Create your own AI Module

(Coming Soon)

### Connect to a Server

Once you've chosen a compute provider and an AI module, you can connect to the server via the commandline.

```
from daimon_sdk import Daimon

server_address = "https://node0.naptha.ai/"
daimon = Daimon(server_address)
daimon.login(username)
```

## Run module

```
# usage: daimon run <module_id> <win_id> <module args>
daimon run lot:e7pou44qbji8thduz9w9 wins:432tslnhplglb5gj5mz5 --prompt "what is the capital of france?"
```

## Check how much you spent

```
daimon purchases
```

# Run a Node

You can run your own Daimon node and earn rewards. Follow the instructions at https://github.com/NapthaAI/daimon-node