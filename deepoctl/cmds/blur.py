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

def main(args, force=False):
    workflow = wa.get_workflow(args)
    inputs = io_data.get_input(args.input)
    blur = io_data.BlurOutputData()

    with io_data.get_output(args.output) as output:
        try:
            for frame in inputs:
                if (workflow is not None):
                    detection = workflow.infer(frame).get()
                    detection = detection['outputs'][0]['labels']['predicted']
                else:
                    detection = []
                blurring = blur((frame, detection))
                if (output(blurring)):
                    break
        except KeyboardInterrupt:
            pass
        except:
            logging.error("Unexpected error: %s" % sys.exc_info()[0])