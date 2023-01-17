from collections import deque
from utils import Change, ChangeType


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
        self._undo_queue.append(reversed_change)

    def redo(self):
        last_change = self._undo_queue.pop()
        reversed_change = self._reverse_change(last_change)
        self._done_queue.append(reversed_change)

    def _reverse_change(self, change: Change):
        if change.change_type == ChangeType.CHANGE_DATA:
            change.current_value, change.prev_value = change.prev_value,\
                change.current_value
        elif change.change_type == ChangeType.ADD_ROW:
            pass
        elif change.change_type == ChangeType.DELETE_ROW:
            pass

        return change
        # change according to change type
        # if change data - flip the current and prev data
        # if remove row - ideally the current data will be empty and
        # old data will be the row removed
        # if add row - current data will be the new row and prev data will be
        # empty

    def save_change_list(self):
        pass

    def load_change_list(self):
        pass



