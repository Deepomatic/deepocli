import os
import sys
import json
import logging
import datetime
import progressbar

import deepoctl.io_data as io_data
import deepoctl.workflow_abstraction as wa


def main(args, force=False):
    workflow = wa.get_workflow(args)
    inputs = io_data.get_input(args.input)

    with io_data.get_output(args.output) as output:
        try:
            for frame in inputs:
                detection = workflow.infer(frame).get()
                detection = detection['outputs'][0]['labels']['predicted']
                if (output(detection)):
                    break
        except KeyboardInterrupt:
            pass
        except:
            logging.error("Unexpected error: %s" % sys.exc_info()[0])