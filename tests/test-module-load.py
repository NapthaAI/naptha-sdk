import json
from typing import List
from naptha_sdk.configs import OrchestratorDeployment, setup_module_deployment
import asyncio
from pydantic import BaseModel

async def main():
    deployment = await setup_module_deployment("orchestrator", "configs/orchestrator_deployments.json", "http://localhost:8000")
    print(deployment)

if __name__ == "__main__":
    asyncio.run(main())