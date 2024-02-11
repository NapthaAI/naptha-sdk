import asyncio
import base64
from daimon_sdk_python.daimon import Daimon
from proto.chatflowmodule import job_pb2 as job_chatflowmodule
import time

async def main():

    server_address = "https://node0.naptha.ai/"
    server_address = "http://localhost:7001"

    username = 'user:buyer1'
    password = "buyer1pass"

    daimon = Daimon(username, password, server_address)

    prompt = "Tell me a joke."

    request = job_chatflowmodule.Request()
    request.prompt = prompt
    binary_data = request.SerializeToString()
    base64_data = base64.b64encode(binary_data)
    base64_string = base64_data.decode('utf-8')

    template_job = {
        'consumer': username,
        'auction_ref': "wins:3cor974gktqez1x41fu9", 
        # 'lot': "lot:krbv1ono18teadg9ogpy",
        'job_type': 'template',
        'request': {"encoded": base64_string},
        "desc": "chatflowmodule",
        # "processor": "node:0",
        'template_params': {
            'template_name': "chatflowmodule",
            'template_args': {}
        }
    }

    job = await daimon.run_task(template_job)

    while True:
        j = await daimon.check_task({"id": job['id']})

        status = j['status']
        print(status)   

        if status == 'completed':
            break
        if status == 'error':
            break

        time.sleep(3)

    if j['status'] == 'completed':
        print(j['reply'])
    else:
        print(j['error_message'])

if __name__=="__main__":
    asyncio.run(main())