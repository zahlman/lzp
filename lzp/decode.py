# standard library
from functools import partial
from zlib import adler32 as compute_checksum


def display_checksum(value):
    return value.to_bytes(4, 'big').hex(' ', 1)


class RAMPatchStream:
    """Treats multiple input and output files as a single, contiguous stream.
    This implementation keeps everything in memory."""
    def __init__(self, sources, checksums):
        ls, lc = len(sources), len(checksums)
        if ls != lc:
            raise ValueError("should have {lc} sources, have {ls}")
        self._buffer = bytearray()
        for source, expected in zip(sources, checksums):
            with open(source, 'rb') as f:
                data = f.read()
            actual = compute_checksum(data)
            if actual != expected:
                source_err = f'bad checksum for {source}'
                expected_err = f'expected: <{display_checksum(expected)}>'
                actual_err = f'actual: <{display_checksum(actual)}>'
                raise ValueError(f'{source_err} ({expected_err} {actual_err})')
            self._buffer.extend(data)
        self._position = 0
        self._out_start = len(self._buffer)


    def dump(self, out):
        with open(out, 'wb') as f:
            f.write(self._buffer[self._out_start:])


    def copy(self, amount):
        for i in range(amount):
            self._buffer.append(self._buffer[self._position])
            self._position += 1


    def append(self, data):
        self._buffer.extend(data)


    def move(self, distance):
        self._position = (self._position + distance) % len(self._buffer)


def raw(amount, stream):
    data = stream.read(amount)
    if len(data) < amount:
        raise IOError("premature end of stream")
    return data


def _data(amount, stream):
    return int.from_bytes(raw(amount, stream), 'big')


byte = partial(_data, 1)
quad = partial(_data, 4)


def number(source, result):
    shift, more = 0, 0x80
    while more:
        b = byte(source)
        more, value = b & 0x80, b & 0x7f
        result |= (value << shift)
        shift += 7
    return result


def command(source, destination, value):
    direction, value = value & 0x80, value & 0x7f
    if value == 0:
        if direction:
            destination.copy(number(source, 1))
        else:
            return False
    elif value == 1:
        amount = number(source, 3) if direction else 1
        destination.append(raw(amount, source))
    else:
        destination.move(number(source, 1) * (-1 if direction else 1))
        destination.copy(value)
    return True


def process(patch, out, *sources):
    with open(patch, 'rb') as f:
        if raw(3, f) != b'LZP':
            raise ValueError('bad signature')
        source_count = byte(f)
        checksums = [quad(f) for _ in range(source_count)]
        destination = RAMPatchStream(sources, checksums)
        while command(f, destination, byte(f)):
            pass
    destination.dump(out)
