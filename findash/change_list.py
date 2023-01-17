from collections import deque
from utils import Change


class ChangeList:
    def __init__(self):
        self._done_queue = deque()
        self._undo_queue = deque()

    def append(self, change: Change):
        if not isinstance(change, Change):
            raise ValueError('ChangeList only accepts items'
                             'of type Change')
        self._done_queue.append(change)

    def undo(self):
        last_change = self._done_queue.pop()
        reversed_change = self._reverse_change(last_change)

    def _reverse_change(self, change: Change):
        pass
        # change according to change type
        # if change data - flip the current and prev data
        # if remove row - ideally the current data will be empty and
        # old data will be the row removed
        # if add row - current data will be the new row and prev data will be
        # empty




