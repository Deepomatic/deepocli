import os
import json
import logging
import datetime
import progressbar

import deepoctl.input_data as input_data
import deepoctl.workflow_abstraction as wa


def main(args, force=False):
    files = input_data.get_files(args.path)
    workflow = wa.get_workflow(args)

    n_files = 0
    n_processed = 0
    n_calls = 0
    n_errors = 0
    for file in files:
        output_file = workflow.get_json_output_filename(file)
        n_files += 1
        if force or not os.path.isfile(output_file):
            _, nc, ne = get_inference_results_on_file(workflow, file)
            n_calls += nc
            n_errors += ne

    logging_fn = logging.warning if n_errors > 0 else logging.info
    logging_fn('{} files processed, {} skipped because already processed'.format(n_processed, n_files - n_processed))
    logging_fn('{} errors over {} inference calls'.format(n_errors, n_calls))

def get_inference_results_on_file(workflow, file):
    n_calls = 0
    n_errors = 0
    frame_results = []
    data_point = input_data.open_file(file)
    logging.info('Infering on {}'.format(file))
    with progressbar.ProgressBar(max_value=data_point.get_frame_number(), redirect_stdout=True) as bar:
        fps = data_point.fps()
        for i, result in enumerate(get_inference_results_on_frames(workflow, data_point)):
            bar.update(i)
            n_calls += 1
            if result is None:
                logging.error('Error on frame {}'.format(i))
                n_errors += 1
            frame_results.append({
                'frame_index': i,
                'frame_timestamp': float(i) / fps if fps > 0 else 0,
                'results': result
            })

    results = {
        'time': datetime.datetime.utcnow().isoformat(),
        'frames': frame_results
    }
    with open(workflow.get_json_output_filename(file), 'w') as f:
        json.dump(results, f)
    return results, n_calls, n_errors

def get_inference_results_on_frames(workflow, data_point):
    batch = []
    for frame in data_point.get_frames():
        # Perform inference
        batch.append(workflow.infer(frame))
        if len(batch) >= 100:
            for result in batch:
                yield result.get()
            batch = []

    # Process final batch
    for result in batch:
        yield result.get()
