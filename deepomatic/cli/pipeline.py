import os
import sys
import logging
import threading
from .thread_base import Pool, Thread, MainLoop, CurrentMessages, blocking_lock, QUEUE_MAX_SIZE
from .cmds.infer import PrepareInferenceThread, SendInferenceGreenlet, ResultInferenceGreenlet
from tqdm import tqdm
from .common import TqdmToLogger, Queue
from .frame import CurrentFrames
from .input_data import InputThread, get_input, InputData
from .output_data import OutputThread, get_outputs
from .workflow import get_workflows, AbstractWorkflow
from .cmds.infer import BlurImagePostprocessing, DrawImagePostprocessing

LOGGER = logging.getLogger(__name__)

# patch the classes TODO: better way
def AbstractWorkflow_to_stages(self, queues, i, current_frames, exit_event, infinite=False):
    input_queue = queues[i]
    output_queue = queues[i+1]
    queue = Queue(maxsize=output_queue.maxsize)
    # Send inference
    skip = output_queue if infinite else None
    send_inference = Pool(1, SendInferenceGreenlet, thread_args=(exit_event, input_queue, queue, current_frames, self, skip))
    # Gather inference predictions from the worker(s)
    result_inference = Pool(1, ResultInferenceGreenlet, thread_args=(exit_event, queue, output_queue, current_frames, self))
    return [
        send_inference,
        result_inference
    ]

AbstractWorkflow.stages = AbstractWorkflow_to_stages

def InputData_to_stages(self, queues, i, current_frames, exit_event):
    output_queue = queues[i]
    queue = Queue(output_queue.maxsize)
    # Input frames
    input_thread = Pool(1, InputThread, thread_args=(exit_event, None, queue, iter(self)))

    # Encode image into jpeg
    prepare_thread = Pool(1, PrepareInferenceThread, thread_args=(exit_event, queue, output_queue, current_frames))

    return [
        input_thread,
        prepare_thread
    ]

InputData.stages = InputData_to_stages

class Pipeline(object):
    @classmethod
    def from_kwargs(cls, kwargs):
         # build pipeline
        input = get_input(kwargs)
        workflows = get_workflows(kwargs)
        outputs = get_outputs(kwargs)

        postprocessing = (DrawImagePostprocessing(**kwargs) if kwargs['command'] == 'draw'
                            else BlurImagePostprocessing(**kwargs) if kwargs['command'] == 'blur'
                            else None)
        return cls(input, workflows, outputs, postprocessing)

    def __init__(self, input, workflows, outputs, postprocessing, output_queue=None, queue_max_size=QUEUE_MAX_SIZE):
        # TODO: might need to rethink the whole pipeling for infinite streams
        # IMPORTANT: maxsize is important, it allows to regulate the pipeline and avoid to pushes too many requests to rabbitmq when we are already waiting for many results
        queues = [Queue(maxsize=queue_max_size) for _ in range(
            len(workflows) + 1
        )]

        self.exit_event = threading.Event()
        self.workflows = workflows
        self.current_frames = CurrentFrames()

        # Initialize progress bar
        frame_count = input.get_frame_count()
        max_value = int(frame_count) if frame_count >= 0 else None
        tqdmout = TqdmToLogger(LOGGER, level=LOGGER.getEffectiveLevel())
        pbar = tqdm(total=max_value, file=tqdmout, desc='Input processing', smoothing=0)

        pools = []
        pools.extend(input.stages(queues, 0, self.current_frames, self.exit_event))
        for i, workflow in enumerate(self.workflows):
            pools.extend(workflow.stages(queues, i, self.current_frames, self.exit_event, input.is_infinite()))

        # Output frames/predictions
        pools.append(Pool(1, OutputThread, thread_args=(self.exit_event, queues[-1], output_queue, self.current_frames, pbar.update, outputs, postprocessing)))

        self.loop = MainLoop(pools, queues, pbar, self.exit_event, self.current_frames, self.close)


    def run(self):
        try:
            stop_asked = self.loop.run_forever()
        except Exception:
            self.cleanup()
            raise
    
        # If the process encountered an error, the exit code is 1.
        # If the process is interrupted using SIGINT (ctrl + C) or SIGTERM, the queues are emptied and processed by the
        # threads, and the exit code is 0.
        # If SIGINT or SIGTERM is sent again during this shutdown phase, the threads are killed, and the exit code is 2.
        if self.exit_event.is_set():
            sys.exit(1)
        elif stop_asked >= 2:
            sys.exit(2)

    def cleanup(self):
        self.loop.cleanup()

    def stop(self, force=False):
        if force:
            for pool in self.loop.pools:
                pool.stop()

            # clearing queues to make sure a thread
            # is not blocked in a queue.put() because of maxsize
            self.loop.clear_queues()
        else:
            self.loop.stop()

    def close(self):
        for workflow in self.workflows:
            workflow.close()
