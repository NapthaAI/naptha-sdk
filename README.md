
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
          #%#%#%%#               Decentralized Compute for Multi-Agent Co-Ops   
                                                                www.naptha.ai

# Daimon Python SDK

## Install

```
pip install daimon-sdk
```

## Get Started

### Create an Acount

Create an account on the [Hub](https://hub.naptha.ai/). You get 1000 free NPT credits when you join. 

### Explore Coworkers on the Network

Navigate to the Coworkers page. Coworkers are users that run full compute nodes on the network, and engage in cooperations (Coops) for a set fee. 

Alternatively, you can use the CLI to see a list of available Coworkers:

```
daimon coworkers
```

### Check out available Co-Ops

Navigate to the Co-Ops page. You can think of a Co-Op like a decentralized workflow or app that you can take part in with one or more Coworkers. Rather than running on a central server, Co-Ops can run across many compute nodes with many local data sources, opening up new use cases. Co-Ops typically involve one or more LLMs, along with humans in the loop. Coworkers can set a price for running Co-Ops. 

You can also use the CLI to explore available Co-Ops that you can take part in with Coworkers, along with their price:

```
daimon coops
```

### Create your own Co-Op

(Coming Soon)

### Connect to a Coworker and Run a Co-Op

Once you've found a Coworker and a Co-Op you'd like to engage in, you can run and view the results using the Hub. 

Alternatively, you can use the commandline tool to connect with the Coworker and run the Co-Op

```
from daimon_sdk import Daimon

coworker_address = "https://node0.naptha.ai/"
daimon = Daimon(coworker_address)
daimon.login(username)
daimon.run_task("chat-coop", prompt="what is the capital of france?")
```

## Check how much you spent

```
daimon purchases
```

# Run a Node

You can run your own Daimon node to become a Coworker, and earn rewards for engaging in Co-Ops. Follow the instructions at https://github.com/NapthaAI/daimon-node