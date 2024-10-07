from naptha_sdk.utils import get_logger
import time

logger = get_logger(__name__)

class Task:
    def __init__(self, 
        name, 
        fn, 
        worker_node_url, 
        orchestrator_node, 
        flow_run, 
        cfg,
        task_engine_cls,
        node_cls,
    ):
        self.name = name
        self.fn = fn
        self.orchestrator_node = orchestrator_node
        self.flow_run = flow_run
        self.task_engine_cls = task_engine_cls
        self.worker_node_url = worker_node_url

    async def __call__(self, *args, **kwargs):
        return await run_task(
            task=self, 
            parameters=kwargs, 
            flow_run=self.flow_run, 
            task_engine_cls=self.task_engine_cls,
        )
    
async def run_task(task, parameters, flow_run, task_engine_cls) -> None:
    task_engine = task_engine_cls(flow_run)
    await task_engine.init_run(task, parameters)
    try:
        await task_engine.start_run()
        while True:
            if task_engine.agent_run.status == "error":
                await task_engine.fail()
                break
            else:
                await task_engine.complete()
                break
            time.sleep(3)
        return task_engine.agent_result[-1]
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        await task_engine.fail()