class VideoStream(object):
    def __init__(self):
        self.queue = []
        self.closed = False

    def add_data(self, data):
        data = data[2:] # ???
        self.queue.append(data)

    def read(self, size):
        # Default argument only called once
        data = bytes()
        print(len(self.queue))
        try:
            while self.queue and len(data) + len(self.queue[0]) < size:
                data = data + self.queue[0]
                del self.queue[0]
        except Exception as exc:
            print(exc)
        return data

    def seek(self, offset, whence):
        return -1 # ???
