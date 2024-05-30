from naptha_sdk.task_engine import run_task

class Task:
    def __init__(self, name, fn, worker_node, orchestrator_node, task_run):
        self.name = name
        self.fn = fn
        self.worker_node = worker_node
        self.orchestrator_node = orchestrator_node
        self.task_run = task_run

        self.consumer = {
            "public_key": task_run["consumer_id"].split(':')[1],
            'id': task_run["consumer_id"],
        }

    async def __call__(self, *args, **kwargs):
        return await run_task(task=self, task_run=self.task_run, parameters=kwargs)