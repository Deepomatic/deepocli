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

class DrawThread(infer.InferenceThread):
    def __init__(self, input_queue, output_queue, **kwargs):
        super(DrawThread, self).__init__(input_queue, output_queue, **kwargs)
        self.process = io_data.DrawOutputData(**kwargs)

    def processing(self, name, frame, prediction):
        return self.process(name, frame, prediction)


def main(args, force=False):
    try:
        io_data.input_loop(args, DrawThread)
    except KeyboardInterrupt:
        pass