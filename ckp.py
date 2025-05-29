import struct
from contextlib import contextmanager
from os import PathLike
from pathlib import Path


@contextmanager
def progress_manager(file_path: str | PathLike[str]):
    ckpts = []
    file_path = Path(file_path)
    if file_path.exists():
        with open(file_path, 'rb+') as fd:
            (amount,) = struct.unpack('@L', fd.read(8))

            b = fd.read(1)
            while b:
                topic = b''
                while b != b'\n':
                    topic += b
                    b = fd.read(1)

                (page,) = struct.unpack('@h', fd.read(2))
                ckpts.append(Checkpoint(topic.decode(), page))
                b = fd.read(1)
    else:
        amount = 0
        file_path.touch()

    manager = ProgressManager(amount, ckpts)
    yield manager
    manager.save(file_path)


class Checkpoint:
    def __init__(self, topic_name: str, page: int = 0, context: 'ProgressManager | None' = None):
        self.page = page
        self.topic_name = topic_name
        self.context = context


class ProgressManager:
    def __init__(self, amount: int, checkpoints: list[Checkpoint]):
        self.amount = amount
        self.__checkpoints = checkpoints
        for ckpt in checkpoints:
            ckpt.context = self

    def save(self, file_path: str | PathLike[str]):
        with open(file_path, 'wb+') as fd:
            fd.write(struct.pack('@L', self.amount))
            for ckpt in self:
                fd.write(ckpt.topic_name.encode())
                fd.write(b'\n')
                fd.write(struct.pack('@h', ckpt.page))


    def __getitem__(self, item: str) -> Checkpoint:
        try:
            return next(ckp for ckp in self.__checkpoints if ckp.topic_name == item)
        except StopIteration:
            ckpt = Checkpoint(item, context=self)
            self.__checkpoints.append(ckpt)
            return ckpt

    def __len__(self):
        return len(self.__checkpoints)

    def __iter__(self):
        return iter(self.__checkpoints)

    def append(self, item: Checkpoint):
        self.__checkpoints.append(item)
