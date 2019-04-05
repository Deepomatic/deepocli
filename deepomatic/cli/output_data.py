import os
import sys
import logging
import json
import copy
import cv2
import imutils
from .thread_base import ThreadBase, POP_TIMEOUT
from .cmds.studio_helpers.vulcan2studio import transform_json_from_vulcan_to_studio

try:
    from Queue import Empty
except ImportError:
    from queue import Empty

DEFAULT_FPS = 25


def save_json_to_file(json_data, json_path):
    try:
        with open('%s.json' % json_path, 'w') as file:
            logging.info('Writing %s.json' % json_path)
            json.dump(json_data, file)
    except Exception:
        logging.error("Could not save file {} in json format.".format(json_path))
        raise

    return


def get_output(descriptor, kwargs):
    if descriptor is not None:
        if DirectoryOutputData.is_valid(descriptor):
            return DirectoryOutputData(descriptor, **kwargs)
        elif ImageOutputData.is_valid(descriptor):
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


class OutputThread(ThreadBase):
    def __init__(self, exit_event, input_queue, on_progress=None, **kwargs):
        super(OutputThread, self).__init__(exit_event, 'OutputThread', input_queue)
        self.args = kwargs
        self.on_progress = on_progress
        self.outputs = get_outputs(self.args.get('outputs', None), self.args)
        self.frames_done = {}
        self.frame_to_output = 0

    def close(self):
        self.frames_done = {}
        self.frame_to_output = 0
        for output in self.outputs:
            output.close()

    def loop_impl(self):
        # looking into frames we popped earlier
        frame = self.frames_done.pop(self.frame_to_output, None)
        if frame is None:
            try:
                frame = self.input_queue.get(timeout=POP_TIMEOUT)
                self.input_queue.task_done()
            except Empty:
                return

            if self.frame_to_output != frame.frame_number:
                self.frames_done[frame.frame_number] = frame
                return

        for output in self.outputs:
            output.output_frame(frame)
        self.frame_to_output += 1
        if self.on_progress:
            self.on_progress(self.frame_to_output)


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
        path = self._descriptor
        try:
            path = path % self._i
        except TypeError:
            pass
        finally:
            self._i += 1
            if frame.output_image is not None:
                logging.info('Writing %s' % path)
                cv2.imwrite(path, frame.output_image)
            else:
                logging.warning('No frame to output.')


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
        self._fps = kwargs['fps'] if kwargs['fps'] else DEFAULT_FPS
        self._writer = None

    def close(self):
        if self._writer is not None:
            self._writer.release()
        self._writer = None

    def output_frame(self, frame):
        if frame.output_image is None:
            logging.warning('No frame to output.')
        else:
            if self._writer is None:
                logging.info('Writing %s' % self._descriptor)
                self._writer = cv2.VideoWriter(self._descriptor, self._fourcc,
                                               self._fps, (frame.output_image.shape[1],
                                                           frame.output_image.shape[0]))
            self._writer.write(frame.output_image)


class DirectoryOutputData(OutputData):
    @classmethod
    def is_valid(cls, descriptor):
        return (os.path.exists(descriptor) and os.path.isdir(descriptor))

    def output_frame(self, frame):
        path = os.path.join(self._descriptor, frame.name)
        if frame.output_image is not None:
            logging.info('Writing %s.jpeg' % path)
            cv2.imwrite('%s.jpeg' % path, frame.output_image)


class StdOutputData(OutputData):
    def __init__(self, **kwargs):
        super(StdOutputData, self).__init__(None, **kwargs)

    def output_frame(self, frame):
        if frame.output_image is None:
            print(json.dumps(frame.predictions))
        else:
            # https://stackoverflow.com/questions/908331/how-to-write-binary-data-to-stdout-in-python-3
            sys.stdout.buffer.write(frame.output_image[:, :, ::-1].tobytes())


class DisplayOutputData(OutputData):
    def __init__(self, **kwargs):
        super(DisplayOutputData, self).__init__(None, **kwargs)
        self._fps = kwargs.get('fps', DEFAULT_FPS)
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
            logging.warning('No frame to output.')
        else:
            cv2.imshow(self._window_name, frame.output_image)
            if cv2.waitKey(self._fps) & 0xFF == ord('q'):
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
                # we deepcopy to avoid surprises if another output modify the frame.predictions
                self._all_predictions.append(copy.deepcopy(predictions))
        # Otherwise we write them to file directly
        else:
            json_path = os.path.splitext(self._descriptor % self._i)[0]
            save_json_to_file(predictions, json_path)
