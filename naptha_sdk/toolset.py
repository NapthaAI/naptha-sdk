from naptha_sdk.client.node import Node, HTTP_TIMEOUT
from naptha_sdk.schemas import ToolsetLoadRepoRequest, ToolsetListRequest, ToolsetList, SetToolsetRequest, ToolsetDetails, ToolsetRequest, ToolRunRequest, ToolRunResult
from naptha_sdk.utils import get_logger
from httpx import HTTPStatusError, RemoteProtocolError
import httpx
import json

logger = get_logger(__name__)

class Toolset:
    def __init__(self,
        worker_node_url,
        agent_id,
        *args,
        **kwargs
    ):
        
        self.agent_id = agent_id
        self.worker_node_url = worker_node_url
        
    async def load_or_add_tool_repo_to_toolset(self, toolset_name, repo_url):
        logger.info(f"Loading tool repo to toolset on worker node {self.worker_node_url}")
        try:
            request = ToolsetLoadRepoRequest(
                agent_id=self.agent_id,
                repo_url=repo_url, 
                toolset_name=toolset_name)


            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
                load_repo_response = await client.post(
                    f"{self.worker_node_url}/tool/add_tool_repo_to_toolset",
                    json=request.model_dump()
                )
                load_repo_response.raise_for_status()
                logger.info(f"Loaded repo {repo_url} into toolset {toolset_name}")
        except (HTTPStatusError, RemoteProtocolError) as e:
            print(f"Failed to load repo: {e}")
            raise
        except Exception as e:
            print(f"Error loading repo: {e}")
            raise

    async def get_toolset_list(self):
        logger.info(f"Getting toolset list from worker node")
        try:
            request = ToolsetListRequest(agent_id=self.agent_id)
            
            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
                # Send agent_id as a query parameter
                toolset_list_response = await client.post(
                    f"{self.worker_node_url}/tool/get_toolset_list",
                    json=request.model_dump()
                )
                toolset_list_response.raise_for_status()
                result = ToolsetList(**json.loads(toolset_list_response.text))
                logger.info(result)
                return result
        except (HTTPStatusError, RemoteProtocolError) as e:
            print(f"Failed to get toolset list: {e}")
            raise
        except Exception as e:
            print(f"Error getting toolset list: {e}")
            raise

    async def set_toolset(self, toolset_name):
        logger.info(f"Setting toolset")
        try:
            request = SetToolsetRequest(agent_id=self.agent_id, toolset_name=toolset_name)
            
            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
                toolset_response = await client.post(
                    f"{self.worker_node_url}/tool/set_toolset",
                    json=request.model_dump()
                )
                toolset_response.raise_for_status()
                result = ToolsetDetails(**json.loads(toolset_response.text))
                
                logger.info(f'Toolset {result.name} loaded')
                # print description with newlines
                for line in result.description.split("\n"):
                    logger.info(f"   {line}")

        except (HTTPStatusError, RemoteProtocolError) as e:
            print(f"Failed to set toolset: {e}")
            raise
        except Exception as e:
            print(f"Error setting toolset: {e}")
            raise

    async def get_current_toolset(self):
        logger.info(f"Getting toolset")
        try:
            request = ToolsetRequest(agent_id=self.agent_id)
            
            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
                toolset_list_response = await client.post(
                    f"{self.worker_node_url}/tool/get_current_toolset",
                    json=request.model_dump()
                )
                toolset_list_response.raise_for_status()
                result = ToolsetDetails(**json.loads(toolset_list_response.text))
                logger.info(f'Toolset {result.name} loaded')
                # print description with newlines
                for line in result.description.split("\n"):
                    logger.info(f"   {line}")
        except (HTTPStatusError, RemoteProtocolError) as e:
            print(f"Failed to get toolset: {e}")
            raise
        except Exception as e:
            print(f"Error getting toolset: {e}")
            raise

    async def run_tool(self, toolset_name, tool_name, params):
        logger.info(f"Running Tool: {toolset_name}.{tool_name}({params})")
        try:
            request = ToolRunRequest(
                tool_run_id="1",
                agent_id=self.agent_id,
                toolset_id=toolset_name,
                tool_id=tool_name,
                params=params
            )

            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
                tool_run_response = await client.post(
                    f"{self.worker_node_url}/tool/run_tool",
                    json=request.model_dump()
                )
                tool_run_response.raise_for_status()
                logger.info(f"{toolset_name}.{tool_name}({params}):")
                result = ToolRunResult(**json.loads(tool_run_response.text))
                logger.info(result.result)
        except (HTTPStatusError, RemoteProtocolError) as e:
            print(f"Failed to run tool: {e}")
            raise
        except Exception as e:
            print(f"Error running tool: {e}")
            raise