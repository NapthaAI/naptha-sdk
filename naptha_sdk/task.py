from naptha_sdk.task_engine import run_task

class Task:
    def __init__(self, name, fn, worker_node, orchestrator_node, flow_run):
        self.name = name
        self.fn = fn
        self.worker_node = worker_node
        self.orchestrator_node = orchestrator_node
        self.flow_run = flow_run

    async def __call__(self, *args, **kwargs):
        return await run_task(task=self, flow_run=self.flow_run, parameters=kwargs)