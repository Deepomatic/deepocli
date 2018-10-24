import os
import sys
import io
import json
import cv2
import logging
import progressbar
import numpy as np
# from PIL import Image, ImageDraw, ImageFont

import deepoctl.cmds.infer as infer
# import deepoctl.input_data as input_data
import deepoctl.io_data as io_data
import deepoctl.workflow_abstraction as wa

# font_size = 20
# font = ImageFont.truetype(os.path.join(os.path.dirname(__file__), '..', 'fonts', 'calibri.ttf'), font_size)

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

    # color = (196, 29, 196)
    # for (input_type, input_path) in inputs:
    #     if (input_type is 'file'):
    #         output = workflow.get_json_output_filename(input_path)
    #         if not os.path.isfile(output):
    #             results, _, _ = infer.get_inference_results_on_file(workflow, input_path)
    #         else:
    #             with open(output, 'r') as f:
    #                 results = json.load(f)
    #     elif (input_type is 'stream'):
    #         infer.get_inference_results_on_stream(input_path)
    #     elif (input_type is 'device'):
    #         infer.get_inference_results_on_stream(device)

    #     results = results['frames']

    #     result_index = 0
    #     data_point = input_data.open_file(input_path)
    #     logging.info('Drawing on {}'.format(output))
    #     with progressbar.ProgressBar(max_value=data_point.get_frame_number(), redirect_stdout=True) as bar:
    #         data_point.prepare_draw(workflow.display_id)
    #         for i, frame in enumerate(data_point.get_frames()):
    #             bar.update(i)
    #             image = Image.open(io.BytesIO(frame))

    #             boxes = []
    #             if result_index < len(results) and i == results[result_index]['frame_index']:
    #                 r = results[result_index]['results']
    #                 if r is not None:  # might be None in case of error
    #                     predicted = r['outputs'][0]['labels']['predicted']
    #                     result_index += 1
    #                     # Draw labels with Pillow
    #                     draw_context = ImageDraw.Draw(image)
    #                     for region in predicted:
    #                         if region['roi'] is None:
    #                             draw_label(draw_context, region['label_name'], 10, 10)
    #                             break
    #                         else:
    #                             width, height = image.size
    #                             x0 = int(region['roi']['bbox']['xmin'] * width)
    #                             y0 = int(region['roi']['bbox']['ymin'] * height)
    #                             x1 = int(region['roi']['bbox']['xmax'] * width)
    #                             y1 = int(region['roi']['bbox']['ymax'] * height)
    #                             boxes.append(((x0, y0), (x1, y1)))
    #                             draw_label(draw_context, region['label_name'], x0 + 5, y0 + 5, color)

    #             # Draw boxes with OpenCV (Pillow does cannot control box outline width)
    #             image = np.array(image)[:, :, ::-1].copy()  # switch from RGB to BGR
    #             for cmin, cmax in boxes:
    #                 cv2.rectangle(image, cmin, cmax, (color[2], color[1], color[0]), 3)
    #             data_point.add_frame(image)
    #         data_point.finalize_draw()


# def draw_label(draw_context, text, x0, y0, color):
#     width, height = draw_context.textsize(text, font=font)
#     margin = 4
#     total_height = height + 2 * margin
#     overlap = 0
#     draw_context.chord([x0, y0, x0 + total_height, y0 + total_height], 90, 270, fill=color, outline=color)
#     draw_context.rectangle([x0 + total_height / 2, y0, x0 + total_height / 2 + width - 2 * overlap, y0 + total_height], fill=color, outline=color)
#     draw_context.chord([x0 + width - 2 * overlap, y0, x0 + total_height + width - 2 * overlap, y0 + total_height], 270, 90, fill=color, outline=color)
#     draw_context.text([x0 + total_height / 2 - overlap, y0 + margin - 1], text, fill=(255, 255, 255), font=font)


