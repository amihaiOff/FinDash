from collections import deque

from findash.utils import Change, ChangeType


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
        return reversed_change

    def redo(self):
        last_change = self._undo_queue.pop()
        reversed_change = self._reverse_change(last_change)
        self._done_queue.append(reversed_change)
        return reversed_change

    def _reverse_change(self, change: Change):
        """
        Reverse a change when moving between done and undo queues.
        :param change:
        :return:
        """
        if change.change_type == ChangeType.CHANGE_DATA:
            change.current_value, change.prev_value = change.prev_value,\
                change.current_value
        elif change.change_type == ChangeType.ADD_ROW:
            change.change_type = ChangeType.DELETE_ROW
        elif change.change_type == ChangeType.DELETE_ROW:
            change.current_value, change.prev_value = change.prev_value, \
                change.current_value
            change.change_type = ChangeType.ADD_ROW

        return change

    def save_change_list(self):
        pass

    def load_change_list(self):
        pass
