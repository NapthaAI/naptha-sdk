import asyncio
from dotenv import load_dotenv
from naptha_sdk.client.naptha import Naptha
from naptha_sdk.modules.agent import Agent
from naptha_sdk.modules.orchestrator import Orchestrator
from naptha_sdk.modules.tool import Tool
from naptha_sdk.modules.kb import KnowledgeBase
from naptha_sdk.modules.memory import Memory
from naptha_sdk.modules.environment import Environment
from naptha_sdk.schemas import AgentDeployment, EnvironmentDeployment, OrchestratorDeployment, KBDeployment, MemoryDeployment, ToolDeployment, AgentRunInput, EnvironmentRunInput, OrchestratorRunInput, KBRunInput, MemoryRunInput, ToolRunInput, NodeConfig, NodeConfigUser, NodeServer
from naptha_sdk.user import sign_consumer_id
import os

load_dotenv(override=True)

naptha = Naptha()

async def check_user():
    user = await naptha.node.check_user(user_input={"public_key": naptha.hub.public_key})

    if user['is_registered']:
        print("Found user...", user)
    else:
        print("No user found. Registering user...")
        user = await naptha.node.register_user(user_input=user)
        print(f"User registered: {user}.")

asyncio.run(check_user())

node = NodeConfigUser(
    user_communication_protocol="http",
    ip="localhost",
    user_communication_port=7001
)

print("Node:", node)

node2 = NodeConfig(
    id="123",
    owner="123",
    public_key="123",
    ip="localhost",
    user_communication_protocol="http",
    node_communication_protocol="ws",
    user_communication_port=7001,
    num_node_communication_servers=1,
    models = [],
    ports = [7002],
    servers = [NodeServer(
        communication_protocol="ws",
        port=7002,
        node_id="123"
    )],
    docker_jobs = False,
)



async def test_agent():


    agent_deployment = AgentDeployment(
        module={"name": "hello_world_agent"},
        node=node
    )
    agent = Agent()

    response = await agent.create(agent_deployment)

    print("Agent created:", response)

    agent_deployment2 = AgentDeployment(
        module={"name": "hello_world_agent"},
        node=node2
    )

    input_params = {
        "firstname": "Sam",
        "surname": "Altman",
    }

    agent_run_input = AgentRunInput(
        consumer_id=naptha.user.id,
        inputs=input_params,
        deployment=agent_deployment2,
        signature=sign_consumer_id(naptha.user.id, os.getenv("PRIVATE_KEY"))
    )

    response = await agent.run(agent_run_input)
    print("Agent response:", response)

async def test_tool():
    

    tool_deployment = ToolDeployment(
        module={"name": "generate_image_tool"},
        node=node
    )   

    tool = Tool()

    response = await tool.create(tool_deployment)
    print("Tool created:", response)

    tool_deployment2 = ToolDeployment(
        module={"name": "generate_image_tool"},
        node=node2
    )

    input_params = {
        "tool_name": "generate_image_tool",
        "prompt": "A beautiful image of a cat",
    }

    tool_run_input = ToolRunInput(
        consumer_id=naptha.user.id,
        inputs=input_params,
        deployment=tool_deployment2,
        signature=sign_consumer_id(naptha.user.id, os.getenv("PRIVATE_KEY"))
    )

    response = await tool.run(tool_run_input)
    print("Tool response:", response)

async def test_kb():
    kb = KnowledgeBase()

    kb_deployment = KBDeployment(
        module={"name": "wikipedia_kb"},
        node=node
    )

    response = await kb.create(kb_deployment)

    print("Knowledge base created:", response)

    kb_deployment2 = KBDeployment(
        module={"name": "wikipedia_kb"},
        node=node2
    )

    input_params = {
        "func_name": "init",
    }

    kb_run_input = KBRunInput(
        consumer_id=naptha.user.id,
        inputs=input_params,
        deployment=kb_deployment2,
        signature=sign_consumer_id(naptha.user.id, os.getenv("PRIVATE_KEY"))
    )

    response = await kb.run(kb_run_input)

    print("Knowledge base response:", response)

async def test_memory():
    memory = Memory()

    memory_deployment = MemoryDeployment(
        module={"name": "cognitive_memory"},
        node=node
    )

    response = await memory.create(memory_deployment)

    print("Memory created:", response)

    memory_deployment2 = MemoryDeployment(
        module={"name": "cognitive_memory"},
        node=node2
    )

    input_params = {
        "func_name": "init",
    }
    
    memory_run_input = MemoryRunInput(
        consumer_id=naptha.user.id,
        inputs=input_params,
        deployment=memory_deployment2,
        signature=sign_consumer_id(naptha.user.id, os.getenv("PRIVATE_KEY"))
    )

    response = await memory.run(memory_run_input)
    print("Memory response:", response)

async def test_environment():
    environment = Environment()

    environment_deployment = EnvironmentDeployment(
        module={"name": "groupchat_environment"},
        node=node
    )

    response = await environment.create(environment_deployment)

    print("Environment created:", response)

    environment_deployment2 = EnvironmentDeployment(
        module={"name": "groupchat_environment"},
        node=node2
    )

    input_params = {
        "function_name": "get_global_state",
    }
    
    environment_run_input = EnvironmentRunInput(
        consumer_id=naptha.user.id,
        inputs=input_params,
        deployment=environment_deployment2,
        signature=sign_consumer_id(naptha.user.id, os.getenv("PRIVATE_KEY"))
    )

    response = await environment.run(environment_run_input)
    print("Environment response:", response)

async def test_orchestrator():
    orchestrator = Orchestrator()


    kb = KnowledgeBase()
    kb_deployment = KBDeployment(
        module={"name": "groupchat_kb"},
        node=node
    )

    agent = Agent()
    agent_deployment = AgentDeployment(
        module={"name": "simple_chat_agent"},
        node=node
    )
    agent_deployment2 = AgentDeployment(
        module={"name": "simple_chat_agent"},
        node=node
    )

    orchestrator_deployment = OrchestratorDeployment(
        module={"name": "multiagent_chat"},
        node=node,
        kb_deployments=[kb_deployment],
        agent_deployments=[agent_deployment, agent_deployment2],
    )

    response = await orchestrator.create(orchestrator_deployment)
    print("Orchestrator created:", response)

    orchestrator_deployment2 = OrchestratorDeployment(
        module={"name": "multiagent_chat"},
        node=node2,
        kb_deployments=[kb_deployment],
        agent_deployments=[agent_deployment, agent_deployment2],
    )

    input_params = {
        "prompt": "lets count up one number at a time. ill start. one.",
    }
    
    orchestrator_run_input = OrchestratorRunInput(
        consumer_id=naptha.user.id,
        inputs=input_params,
        deployment=orchestrator_deployment2,
        signature=sign_consumer_id(naptha.user.id, os.getenv("PRIVATE_KEY"))
    )

    response = await orchestrator.run(orchestrator_run_input)
    print("Orchestrator response:", response)

if __name__ == "__main__":
    asyncio.run(test_orchestrator())



