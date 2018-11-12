import os
import sys
import io
import json
import cv2
import logging
import progressbar
import numpy as np

import deepoctl.cmds.infer as infer
import deepoctl.io_data as io_data
import deepoctl.workflow_abstraction as wa


class BlurThread(infer.InferenceThread):
    def __init__(self, queue, args=(), kwargs=None):
        infer.InferenceThread.__init__(self, queue, args, kwargs)
        self.draw = io_data.BlurOutputData()

    def processing(self, frame, detection):
        return self.draw((frame, detection))

def main(args, force=False):
    try:
        io_data.input_loop(args, BlurThread)
    except KeyboardInterrupt:
        pass
    except:
        logging.error("Unexpected error: %s" % sys.exc_info()[0])