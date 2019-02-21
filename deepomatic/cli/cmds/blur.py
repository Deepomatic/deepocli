import os
import sys
import io
import json
import cv2
import logging
import numpy as np

import deepomatic.cli.cmds.infer as infer
import deepomatic.cli.io_data as io_data
import deepomatic.cli.workflow_abstraction as wa


class BlurThread(infer.InferenceThread):
    def __init__(self, input_queue, output_queue, **kwargs):
        super(BlurThread, self).__init__(input_queue, output_queue, **kwargs)
        self.process = io_data.BlurOutputData(**kwargs)

    def processing(self, name, frame, prediction):
        return self.process(name, frame, prediction)

def main(args, force=False):
    try:
        io_data.input_loop(args, BlurThread)
    except KeyboardInterrupt:
        pass