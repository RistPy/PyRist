class Sender:
    __slots__ = ('iterator', 'send_value')
    def __init__(self, iterator):
        self.iterator = iterator
        self.send_value = None

    def __iter__(self):
        return self._internal(self.iterator.__iter__())

    def _internal(self, base):
        try:
            while True:
                value = base.send(self.send_value)
                self.send_value = None
                yield self.set_send_value, value
        except StopIteration:
            pass

    def set_send_value(self, value):
        self.send_value = value
