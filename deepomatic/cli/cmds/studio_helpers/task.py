# -*- coding: utf-8 -*-
import time

class Task(object):
    def __init__(self, helper, pk=None, files=None):
        self._helper = helper

    def retrieve(self, task_id, wait=True):
        ret = self._helper.get('manage/tasks/{}/'.format(task_id))
        if not wait:
            return ret
        while ret['next'] != None and ret['status'] != 'SUCCESS':
            if ret['status'] in ('FAILURE', 'REVOKED'):
                raise RuntimeError("Task {} stoped with status".format(task_id))
            elif ret['status'] == 'SUCCESS':
                task_id = ret['next']
                ret = self._helper.get('manage/tasks/{}/'.format(task_id))
            else:
                time.sleep(5)
                ret = self._helper.get('manage/tasks/{}/'.format(task_id))
        return ret
