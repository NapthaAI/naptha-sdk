
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

### Connect to a Server

Create an account on the [Hub](https://hub.naptha.ai/). You get 1000 free NPT credits when you join. Explore available compute nodes. 

### Buy Compute

You can buy compute from a specific provider through the app, or via the command line:

```
daimon purchase <auction_id>
daimon purchases
```

### Connect to a Server

Once you've bought credits you can connect to the server.

```
from daimon_sdk import Daimon

server_address = "https://node0.naptha.ai/"
daimon = Daimon(server_address)
daimon.login(username)
```

### Check out existing AI Modules

```
daimon modules
```

### Create your own AI Module

(Coming Soon)

## Run module

```
# usage: daimon run <module_id> <win_id> <module args>
daimon run lot:e7pou44qbji8thduz9w9 wins:432tslnhplglb5gj5mz5 --prompt "what is the capital of france?"
```

# Run a Node

You can run your own Daimon node and earn rewards. Follow the instructions at https://github.com/NapthaAI/daimon-node