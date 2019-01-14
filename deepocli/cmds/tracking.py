import os
import sys
import json
import threading
import logging
import datetime
import progressbar
import numpy as np
import collections
import cv2
import time
from scipy.optimize import linear_sum_assignment
try:
    from Queue import Empty
except ImportError:
    from queue import Empty

import deepocli.cmds.infer as infer
import deepocli.io_data as io_data
import deepocli.workflow_abstraction as wa

class TrackingThread(infer.InferenceThread):
    def __init__(self, input_queue, output_queue, **kwargs):
        super(TrackingThread, self).__init__(
            input_queue, output_queue, **kwargs)
        self.process = io_data.DrawOutputData(**kwargs)

    def run(self):
        try:
            timestamp = -1
            detection = None
            frame = None
            detection_timestamp = -1
            tracking = BetterTracking()
            while True:
                tracks = None
                prediction = None
                # process frame
                try:
                    data = self.input_queue.get(False)
                    if data is None:
                        self.input_queue.task_done()
                        self.output_queue.put(None)
                        return
                    else:
                        timestamp += 1
                        name, frame = data
                        tracks = tracking.onframe(frame, timestamp)

                except Empty:
                    data = None

                # process detection
                if detection is not None:
                    # Already a detection launched
                    prediction = detection.get(block=False)
                    if prediction is None:
                        # prediction not finished
                        pass
                    else:
                        # prediction finished
                        prediction = [predicted
                                      for predicted in prediction['outputs'][0]['labels']['predicted']
                                      if float(predicted['score']) >= float(self._threshold)]
                        # update tracks
                        tracks = tracking.ondetection(
                            prediction, frame, detection_timestamp)
                        # run detection again (if different frame)
                        if self.workflow is not None and frame is not None and detection_timestamp < timestamp:
                            detection = self.workflow.infer(frame)
                            detection_timestamp = timestamp
                        else:
                            detection = None
                else:
                    # Start a new detection
                    if self.workflow is not None and frame is not None and detection_timestamp < timestamp:
                        detection = self.workflow.infer(frame)
                        detection_timestamp = timestamp

                if data is None:
                    # No input frame consumed, wait a little bit
                    time.sleep(0.001)
                else:
                    self.input_queue.task_done()
                    result = self.processing(name, frame, tracks)
                    self.output_queue.put(result)

        except KeyboardInterrupt:
            logging.info('Stopping output')
            while not self.output_queue.empty():
                try:
                    self.output_queue.get(False)
                except Empty:
                    break
                self.output_queue.task_done()
            self.output_queue.put(None)

    def processing(self, name, frame, prediction):
        return self.process(name, frame, prediction)


def main(args, force=False):
    try:
        io_data.input_loop(args, TrackingThread)
    except KeyboardInterrupt:
        pass


############ Tracking #############


class Tracking(object):
    def __init__(self):
        self.start()

    def start(self):
        self.timestamp = 0
        self.tracks = []
        return self.tracks

    def ondetection(self, detection, frame, timestamp):
        start_time = time.time()
        # The detection was computed on frame at timestamp

        # Estimate the location of the detection at self.timestamp
        detection = self._predict(detection, frame, timestamp, self.timestamp)

        # Match the current tracks to the new detection
        matching = self._match(detection, self.tracks)
        mapped, not_mapped_tracks, not_mapped_predictions = matching

        tracks = []
        # Update the mapped tracks
        for (track, detection) in mapped:
            tracks.extend(self._process_mapped(track, detection))

        # Process not mapped tracks
        for track in not_mapped_tracks:
            tracks.extend(self._process_not_mapped_track(track))

        # Process not mapped predictions
        for prediction in not_mapped_predictions:
            tracks.extend(self._process_not_mapped_prediction(prediction))

        # Update the tracking accordingly
        self._update(frame, self.timestamp, tracks)

        # Do nothing for now

        # logging.info('ondetection %d at %d : %f' %
        #              (timestamp, self.timestamp, time.time() - start_time))
        
        return self.tracks

    def onframe(self, frame, timestamp):
        start_time = time.time()
        # A new frame was received at timestamp

        # Process the frame
        self._process(frame, timestamp)

        # Estimate the location of the tracks in the new frame
        tracks = self._predict(self.tracks, frame, self.timestamp, timestamp)

        # logging.info('onframe %d at %d : %f' %
        #              (timestamp, self.timestamp, time.time() - start_time))

        # Update the tracking accordingly
        self._update(frame, timestamp, tracks)

        return self.tracks

    def end(self):
        pass

    def _process(self, frame, timestamp):
        # Process the new frame
        pass

    def _predict(self, detection, frame, start, finish):
        # Propagates the tracks location from start to finish
        return detection

    def _update(self, frame, timestamp, tracks):
        # Update the tracking tracker state
        self.tracks = tracks
        self.timestamp = timestamp

    def _match(self, detection, tracks):
        # Given predictions and tracks, try to find matches
        mapped = []
        not_mapped_tracks = tracks
        not_mapped_prediction = detection
        return mapped, not_mapped_tracks, not_mapped_prediction

    def _process_mapped(self, track, prediction):
        return [prediction]

    def _process_not_mapped_track(self, track):
        return []

    def _process_not_mapped_prediction(self, prediction):
        return [prediction]


class BetterTracking(Tracking):
    def __init__(self):
        super(BetterTracking, self).__init__()
        self.feature_params = dict(maxCorners=100,
                                   qualityLevel=0.3,
                                   minDistance=7,
                                   blockSize=7)  # TODO: in parameters
        self.lk_params = dict(winSize=(15, 15),
                              maxLevel=2,
                              criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 0.03))

        self.max_track_age = 10

        # TODO mask
        self.feature_mask = None

        self.timestamps = {}
        self.corners = {}
        self.optical_flow = {}
        self.frames = {}

    def ondetection(self, detection, frame, timestamp):
        tracks = super(BetterTracking, self).ondetection(
            detection, frame, timestamp)
        # cleanup: no need to keep data from before the last detection timestamp
        self.timestamps = {k: v for k,
                           v in self.timestamps.items() if k >= timestamp}
        self.corners = {k: v for k, v in self.corners.items() if k >= timestamp}
        self.optical_flow = {(t0, t1): v for (
            t0, t1), v in self.optical_flow.items() if t0 >= timestamp}
        self.frames = {k: v for k, v in self.frames.items() if k >= timestamp}

        return tracks

    def _process(self, frame, timestamp):
        # Process the new frame

        # Using gray scale image
        if len(frame.shape) == 3:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Compute optical flow
        if self.timestamp in self.frames:
            old_corners = self.corners[self.timestamp]
            old_frame = self.frames[self.timestamp]

            self.optical_flow[(self.timestamp, timestamp)] = cv2.calcOpticalFlowPyrLK(
                old_frame, frame, old_corners, None, **self.lk_params)

        # Register next timestamp
        self.timestamps[self.timestamp] = timestamp

        # Register next frame
        self.frames[timestamp] = frame

        # Compute corners
        self.corners[timestamp] = cv2.goodFeaturesToTrack(
            frame, mask=self.feature_mask, **self.feature_params)

    def _predict(self, tracks, frame, start, finish):
        assert(start <= finish)
        t0 = start
        # iterate from start to finish
        while t0 < finish:
            t1 = self.timestamps[t0]

            # get mapping between features from t0 to t1
            p1, st, err = self.optical_flow[(t0, t1)]

            good_new = p1[st == 1]
            good_old = self.corners[t0][st == 1]

            movements = [[] for track in tracks]
            # for each mapped feature from t0 to t1
            for new, old in zip(good_new, good_old):
                x0, y0 = new.ravel()
                x1, y1 = old.ravel()

                for movement, track in zip(movements, tracks):
                    bbox = track['roi']['bbox']
                    xmin, ymin = bbox['xmin'], bbox['ymin']
                    xmax, ymax = bbox['xmax'], bbox['ymax']
                    # TODO: weighted
                    # If the feature belongs to the prediction
                    if xmin < x0 < xmax and ymin < y0 < ymax:
                        movement.append(np.array([x1 - x0, y1 - y0]))

            for movement, track in zip(movements, tracks):
                # mean of corners movement
                dx, dy = sum(movement, np.array(
                    [0, 0])) / max(1, len(movement))
                # move bbox
                track['roi']['bbox']['xmin'] += dx
                track['roi']['bbox']['ymin'] += dy
                track['roi']['bbox']['xmax'] += dx
                track['roi']['bbox']['ymax'] += dy
                # TODO: scale
            t0 = t1
        return tracks

    @staticmethod
    def cost(track1, track2):
        # how likely is track1 to be track2 ?
        # unecessarily complicated cost function:
        # TODO: compare labels, cross-correlate thumbnails etc..
        # union
        _w1 = track1['roi']['bbox']['xmax'] - track1['roi']['bbox']['xmin']
        _w2 = track2['roi']['bbox']['xmax'] - track2['roi']['bbox']['xmin']
        _h1 = track1['roi']['bbox']['ymax'] - track1['roi']['bbox']['ymin']
        _h2 = track2['roi']['bbox']['ymax'] - track2['roi']['bbox']['ymin']

        _u1 = _w1 * _h1
        _u2 = _w2 * _h2

        # intersection
        _xa = max(track1['roi']['bbox']['xmin'],
                  track2['roi']['bbox']['xmin'])
        _xb = min(track1['roi']['bbox']['xmax'],
                  track2['roi']['bbox']['xmax'])
        _ya = max(track1['roi']['bbox']['ymin'],
                  track2['roi']['bbox']['ymin'])
        _yb = min(track1['roi']['bbox']['ymax'],
                  track2['roi']['bbox']['ymax'])

        _wi = max(0, _xb - _xa)
        _hi = max(0, _yb - _ya)

        _i = _wi * _hi

        # distance (kindof)

        dw = _wi / (_w1 + _w2 - (_xb - _xa))
        dh = _hi / (_h1 + _h2 - (_yb - _ya))

        # dimension ratio
        _wmin = min(_w1, _w2)
        _wmax = max(_w1, _w2)
        _hmin = min(_h1, _h2)
        _hmax = max(_h1, _h2)

        wr = _wmin / _wmax
        hr = _hmin / _hmax

        _xmin = min(track1['roi']['bbox']['xmin'],
                    track2['roi']['bbox']['xmin'])
        _xmax = max(track1['roi']['bbox']['xmax'],
                    track2['roi']['bbox']['xmax'])
        _ymin = min(track1['roi']['bbox']['xmin'],
                    track2['roi']['bbox']['ymin'])
        _ymax = max(track1['roi']['bbox']['ymax'],
                    track2['roi']['bbox']['ymax'])

        iou = _i / (_u1 + _u2 - _i)

        features = [iou, wr, hr, dw, dh]
        c = 0
        for feature in features:
            c -= np.log(0.001 + feature)
        return c

    def _match(self, detection, tracks):
        cost = np.array([[BetterTracking.cost(old, new)
                          for new in detection] for old in tracks])
        mapped = []
        not_mapped_tracks = tracks
        not_mapped_prediction = detection

        if (len(cost)):
            row_ind, col_ind = linear_sum_assignment(cost)

            mapped = [(tracks[i], detection[j])
                      for i, j in zip(row_ind, col_ind)]
            not_mapped_tracks = [track for i, track in enumerate(
                tracks) if i not in row_ind]
            not_mapped_prediction = [
                track for j, track in enumerate(detection) if j not in col_ind]

        return mapped, not_mapped_tracks, not_mapped_prediction

    def _process_mapped(self, track, prediction):
        # TODO: kalman
        # for now, track takes the prediction's position, score, label
        prediction['roi']['region_id'] = track['roi']['region_id']
        prediction['age'] = track['age'] + 1
        return [prediction]

    def _process_not_mapped_track(self, track):
        # TODO: correlation with last updated thumbnail
        # for now, leave it alive for a few frame
        return [] if track['age'] > self.max_track_age else [track]

    def _process_not_mapped_prediction(self, prediction):
        # TODO: create if score is good enough
        # for now, create tracks
        prediction['age'] = 1
        return [prediction]
