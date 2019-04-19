import os
import sys
import logging
import json
import cv2
import imutils
from .thread_base import Thread
from .common import Empty
from .cmds.studio_helpers.vulcan2studio import transform_json_from_vulcan_to_studio


LOGGER = logging.getLogger(__name__)
DEFAULT_OUTPUT_FPS = 25


try:
    # https://stackoverflow.com/questions/908331/how-to-write-binary-data-to-stdout-in-python-3
    write_bytes_to_stdout = sys.stdout.buffer.write
except AttributeError:
    write_bytes_to_stdout = sys.stdout.write


def save_json_to_file(json_data, json_path):
    try:
        with open('%s.json' % json_path, 'w') as f:
            LOGGER.info('Writing %s.json ..' % json_path)
            json.dump(json_data, f)
            LOGGER.info('Writing %s.json done' % json_path)
    except Exception:
        LOGGER.error("Could not save file {} in json format.".format(json_path))
        raise

    return


def get_output(descriptor, kwargs):
    if descriptor is not None:
        if ImageOutputData.is_valid(descriptor):
            return ImageOutputData(descriptor, **kwargs)
        elif VideoOutputData.is_valid(descriptor):
            return VideoOutputData(descriptor, **kwargs)
        elif JsonOutputData.is_valid(descriptor):
            return JsonOutputData(descriptor, **kwargs)
        elif descriptor == 'stdout':
            return StdOutputData(**kwargs)
        elif descriptor == 'window':
            return DisplayOutputData(**kwargs)
        else:
            raise NameError("Unknown output '{}'".format(descriptor))
    else:
        return DisplayOutputData(**kwargs)


def get_outputs(descriptors, kwargs):
    return [get_output(descriptor, kwargs) for descriptor in descriptors]


class OutputThread(Thread):
    def __init__(self, exit_event, input_queue, output_queue, current_messages,
                 on_progress, postprocessing, **kwargs):
        super(OutputThread, self).__init__(exit_event, input_queue,
                                           output_queue, current_messages)
        self.args = kwargs
        self.on_progress = on_progress
        self.postprocessing = postprocessing
        self.frames_to_check_first = {}
        self.frame_to_output = None
        # Update output fps to default value if none was specified.
        # Logs information only if one of the outputs uses fps.
        if not kwargs['output_fps']:
            kwargs['output_fps'] = DEFAULT_OUTPUT_FPS
            self.outputs = get_outputs(self.args.get('outputs', None), self.args)
            for output in self.outputs:
                if isinstance(output, VideoOutputData) or isinstance(output, DisplayOutputData):
                    logging.info('No --output_fps value specified for output, using default value of {}.'.format(DEFAULT_OUTPUT_FPS))
                    break
        else:
            self.outputs = get_outputs(self.args.get('outputs', None), self.args)

    def close(self):
        self.frames_to_check_first = {}
        self.frame_to_output = None
        for output in self.outputs:
            output.close()

    def can_stop(self):
        return super(OutputThread, self).can_stop() and \
            len(self.frames_to_check_first) == 0

    def pop_input(self):
        # looking into frames we popped earlier
        if self.frame_to_output is None:
            self.frame_to_output = self.current_messages.pop_oldest()
            if self.frame_to_output is None:
                raise Empty()

        frame = self.frames_to_check_first.pop(self.frame_to_output, None)
        if frame is None:
            frame = super(OutputThread, self).pop_input()
        return frame

    def process_msg(self, frame):
        if self.frame_to_output != frame.frame_number:
            self.frames_to_check_first[frame.frame_number] = frame
            return

        if self.postprocessing is not None:
            self.postprocessing(frame)
        else:
            frame.output_image = frame.image  # we output the original image

        for output in self.outputs:
            output.output_frame(frame)
        if self.on_progress:
            self.on_progress()
        self.task_done()
        self.frame_to_output = None


class OutputData(object):
    def __init__(self, descriptor, **kwargs):
        self._descriptor = descriptor
        self._args = kwargs

    def close(self):
        pass

    def output_frame(self, frame):
        # override this to output the results of the frame
        raise NotImplementedError()


class ImageOutputData(OutputData):
    supported_formats = ['.bmp', '.jpeg', '.jpg', '.jpe', '.png']

    @classmethod
    def is_valid(cls, descriptor):
        _, ext = os.path.splitext(descriptor)
        return ext in cls.supported_formats

    def __init__(self, descriptor, **kwargs):
        super(ImageOutputData, self).__init__(descriptor, **kwargs)
        self._i = 0

    def output_frame(self, frame):
        self._i += 1
        path = self._descriptor
        try:
            path = path % self._i
        except TypeError:
            pass
        finally:
            if frame.output_image is not None:
                LOGGER.info('Writing %s' % path)
                cv2.imwrite(path, frame.output_image)
            else:
                LOGGER.warning('No frame to output.')


class VideoOutputData(OutputData):
    supported_formats = ['.avi', '.mp4']

    @classmethod
    def is_valid(cls, descriptor):
        _, ext = os.path.splitext(descriptor)
        return ext in cls.supported_formats

    def __init__(self, descriptor, **kwargs):
        super(VideoOutputData, self).__init__(descriptor, **kwargs)
        ext = os.path.splitext(descriptor)[1]
        if ext == '.avi':
            fourcc = cv2.VideoWriter_fourcc('X', 'V', 'I', 'D')
        elif ext == '.mp4':
            fourcc = cv2.VideoWriter_fourcc('m', 'p', '4', 'v')
        self._fourcc = fourcc
        self._fps = kwargs['output_fps']
        self._writer = None

    def close(self):
        if self._writer is not None:
            self._writer.release()
        self._writer = None

    def output_frame(self, frame):
        if frame.output_image is None:
            LOGGER.warning('No frame to output.')
        else:
            if self._writer is None:
                LOGGER.info('Writing %s' % self._descriptor)
                self._writer = cv2.VideoWriter(self._descriptor, self._fourcc,
                                               self._fps, (frame.output_image.shape[1],
                                                           frame.output_image.shape[0]))
            self._writer.write(frame.output_image)


class StdOutputData(OutputData):
    def __init__(self, **kwargs):
        super(StdOutputData, self).__init__(None, **kwargs)

    def output_frame(self, frame):
        if frame.output_image is None:
            print(json.dumps(frame.predictions))
        else:
            write_bytes_to_stdout(frame.output_image[:, :, ::-1].tobytes())


class DisplayOutputData(OutputData):
    def __init__(self, **kwargs):
        super(DisplayOutputData, self).__init__(None, **kwargs)
        self._fps = kwargs['output_fps']
        self._window_name = 'Deepomatic'
        self._fullscreen = kwargs.get('fullscreen', False)

        if self._fullscreen:
            cv2.namedWindow(self._window_name, cv2.WINDOW_NORMAL)
            if imutils.is_cv2():
                prop_value = cv2.cv.CV_WINDOW_FULLSCREEN
            elif imutils.is_cv3():
                prop_value = cv2.WINDOW_FULLSCREEN
            else:
                assert('Unsupported opencv version')
            cv2.setWindowProperty(self._window_name,
                                  cv2.WND_PROP_FULLSCREEN,
                                  prop_value)

    def output_frame(self, frame):
        if frame.output_image is None:
            LOGGER.warning('No frame to output.')
        else:
            cv2.imshow(self._window_name, frame.output_image)
            try:
                ms = 1000 // int(self._fps)
            except:
                ms = 1
            if cv2.waitKey(ms) & 0xFF == ord('q'):
                cv2.destroyAllWindows()
                cv2.waitKey(1)
                sys.exit()

    def close(self):
        if cv2.waitKey(0) & 0xFF == ord('q'):
            cv2.destroyAllWindows()
            cv2.waitKey(1)


class JsonOutputData(OutputData):
    supported_formats = ['.json']

    @classmethod
    def is_valid(cls, descriptor):
        _, ext = os.path.splitext(descriptor)
        return ext in cls.supported_formats

    def __init__(self, descriptor, **kwargs):
        super(JsonOutputData, self).__init__(descriptor, **kwargs)
        self._i = 0
        self._to_studio_format = kwargs.get('studio_format')
        # Check if the output is a wild card or not
        try:
            descriptor % self._i
            self._all_predictions = None
        except TypeError:
            if self._to_studio_format:
                self._all_predictions = {'tags': [], 'images': []}
            else:
                self._all_predictions = []

    def close(self):
        if self._all_predictions is not None:
            json_path = os.path.splitext(self._descriptor)[0]
            save_json_to_file(self._all_predictions, json_path)

    def output_frame(self, frame):
        self._i += 1
        predictions = frame.predictions
        if self._to_studio_format:
            predictions = transform_json_from_vulcan_to_studio(predictions,
                                                               frame.name,
                                                               frame.filename)
        else:
            predictions['location'] = frame.filename

        if self._all_predictions is not None:
            # If the json is not a wildcard we store prediction to write then to file a the end in close()
            if self._to_studio_format:
                self._all_predictions['images'] += predictions['images']
                self._all_predictions['tags'] = list(
                    set(self._all_predictions['tags'] + predictions['tags'])
                )
            else:
                self._all_predictions.append(predictions)
        # Otherwise we write them to file directly
        else:
            json_path = os.path.splitext(self._descriptor % self._i)[0]
            save_json_to_file(predictions, json_path)
