
import asyncio
import base64
from daimon_sdk_python.hub import Hub

async def main():

    hub_address = "http://localhost:8001"
    hub_endpoint = "ws://localhost:3003/rpc"

    username = "buyer1"
    password = "buyer1pass"

    hub = await Hub(username, password, hub_endpoint)

    purchases = await hub.check_credits({"me": f"user:{username}"})

    print("Purchases: ", purchases)


if __name__=="__main__":
    asyncio.run(main())