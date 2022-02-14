# standard library
from functools import partial
from zlib import adler32 as compute_checksum


def display_checksum(value):
    return value.to_bytes(4, 'big').hex(' ', 1)


class RAMPatchStream:
    """Treats multiple input and output files as a single, contiguous stream.
    This implementation simply keeps everything in memory."""
    def __init__(self, sources):
        self._buffer = bytearray().join(sources)
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


def contents(filename):
    with open(filename, 'rb') as f:
        return f.read()


def _data(amount, stream):
    return int.from_bytes(raw(amount, stream), 'big')


byte = partial(_data, 1)
quad = partial(_data, 4)


def number(source):
    result, shift, more = 0, 0, 0x80
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
            destination.copy(number(source) + 1)
        else:
            return False
    elif value == 1:
        amount = number(source) + 3 if direction else 1
        destination.append(raw(amount, source))
    else:
        destination.move((number(source) + 1) * (-1 if direction else 1))
        destination.copy(value)
    return True


def _verify(f, names, actual):
    # TODO: `zlib.adler32` requires a bytes-like object, so the whole file
    # has to be read into memory even if we want to use a `PatchStream` that
    # checks the files on demand (to save RAM).
    if raw(3, f) != b'LZP':
        raise ValueError('bad signature')
    source_count = byte(f)
    if len(actual) != source_count:
        raise ValueError("should have {lc} sources, have {ls}")
    expected = [quad(f) for _ in range(source_count)]
    for name, a, e in zip(names, actual, expected):
        if a != e:
            source_err = f'bad checksum for {name}'
            expected_err = f'expected: <display_checksum(e)>'
            actual_err = f'actual: <{display_checksum(a)}>'
            raise ValueError(f'{source_err} ({expected_err} {actual_err})')


def process(patch_name, patched_name, *source_names, header=True):
    """Apply a patch.
    `patch_name` -> path to the patch being applied.
    `patched__name` -> path to write as the patched result.
    `source_names` -> paths to input sources that are being patched.
    `header` -> whether the patch contains a header.
    """
    names = list(source_names)
    sources = [contents(s) for s in names]
    with open(patch_name, 'rb') as patch:
        if header:
            _verify(patch, names, [compute_checksum(s) for s in sources])
        destination = RAMPatchStream(sources)
        while command(patch, destination, byte(patch)):
            pass
    destination.dump(patched_name)
