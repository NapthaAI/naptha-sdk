import asyncio
import base64
from daimon_sdk_python.daimon import Daimon
from proto.chatflowmodule import job_pb2 as job_chatflowmodule

async def main():

    # server_address = "https://node0.naptha.ai/"
    server_address = "http://localhost:7001"

    username = 'user:buyer1'
    password = "buyer1pass"

    daimon = Daimon(username, password, server_address)

    tasks = await daimon.check_tasks()

    print('======', tasks)

if __name__=="__main__":
    asyncio.run(main())