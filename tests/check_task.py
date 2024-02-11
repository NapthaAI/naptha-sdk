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

    task = await daimon.check_task({
        "username": username,
        "password": password,
        "id": "consume:76awehm95grpnsegw1nq"
    })


    # template_job = {
    #     'consumer': username,
    #     'auction_ref': "wins:3cor974gktqez1x41fu9", 
    #     'lot': "lot:krbv1ono18teadg9ogpy",
    #     'job_type': 'template',
    #     'request': {"encoded": base64_string},
    #     "desc": "chatflowmodule",
    #     "processor": "node:0",
    #     'template_params': {
    #         'template_name': "chatflowmodule",
    #         'template_args': {}
    #     }
    # }

    print('======', task)

if __name__=="__main__":
    asyncio.run(main())