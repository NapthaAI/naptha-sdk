import json
from typing import Dict, Union
import httpx
from httpx import HTTPStatusError, RemoteProtocolError
from naptha_sdk.schemas import ChatCompletionRequest, NodeConfigUser, ModelResponse
from naptha_sdk.utils import get_logger, node_to_url

logger = get_logger(__name__)
HTTP_TIMEOUT = 300


class InferenceClient:
    def __init__(self, node: NodeConfigUser):
        self.node = node
        self.node_url = node_to_url(node)
        
        self.access_token = None
        logger.info(f"Node URL: {self.node_url}")

    async def run_inference(self, inference_input: Union[ChatCompletionRequest, Dict]) -> Dict:
        """
        Run inference on a node
        
        Args:
            inference_input: The inference input to run inference on
        """
        if isinstance(inference_input, dict):
            inference_input = ChatCompletionRequest(**inference_input)

        endpoint = f"{self.node_url}/inference/chat/completions"

        try:
            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
                headers = {
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {self.access_token}',
                }
                response = await client.post(
                    endpoint,
                    json=inference_input.model_dump(),
                    headers=headers
                )
                print("Response: ", response.text)
                response.raise_for_status()
                return ModelResponse(**json.loads(response.text))
        except HTTPStatusError as e:
            logger.info(f"HTTP error occurred: {e}")
            raise
        except RemoteProtocolError as e:
            error_msg = f"Inference failed to connect to the server at {self.node_url}. Please check if the server URL is correct and the server is running. Error details: {str(e)}"
            logger.error(error_msg)
            raise
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            raise

    async def list_models(self, return_wildcard_routes: bool = False) -> Dict:
        """
        Get list of available models from the node
        
        Args:
            return_wildcard_routes: Whether to return wildcard routes
        """
        endpoint = f"{self.node_url}/inference/models"
        
        try:
            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
                headers = {
                    'Authorization': f'Bearer {self.access_token}',
                }
                params = {"return_wildcard_routes": return_wildcard_routes}
                
                response = await client.get(
                    endpoint,
                    params=params,
                    headers=headers
                )
                response.raise_for_status()
                return json.loads(response.text)
        except HTTPStatusError as e:
            logger.info(f"HTTP error occurred: {e}")
            raise
        except RemoteProtocolError as e:
            error_msg = f"Failed to connect to the server at {self.node_url}. Please check if the server URL is correct and the server is running. Error details: {str(e)}"
            logger.error(error_msg)
            raise
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
            raise