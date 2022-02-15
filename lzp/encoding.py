from .common import compute_checksum, contents


class RAMPatchBuffer:
    def __init__(self, result, sources):
        self._data = b''.join(sources)
        self._read_position = 0
        self._write_position = len(self._data)
        self._data += (result)


    def _abs_distance(self, position):
        # absolute distance from position to self._read_position,
        # treating -1 as an exception.
        size = self._write_position
        if position == -1:
            return size # should be impossibly large
        direct = abs(position - self._read_position)
        result = min(direct, size - direct)
        # should have direct <= size; and if direct == size, then
        # size - direct == 0 which < size unless size == 0.
        # but if size == 0, then we cannot find a match anyway.
        assert result < size
        return result


    def _signed_distance(self, position):
        assert position >= 0
        direct = position - self._read_position
        size = self._write_position
        wraparound = direct + (size if direct < 0 else -size)
        return min((direct, wraparound), key=abs)


    @property
    def remaining(self):
        return len(self._data) - self._write_position


    def _find(self, amount):
        """Look for the specified `amount` of data within the window.
        Return the best position, i.e. closest to the current read position."""
        cursor, start = self._read_position, self._write_position
        if amount > self.remaining:
            return -1 # there isn't that much data to find!
        to_find = self._data[start:start+amount]
        # Look forwards for a match starting at or after self._read_position.
        forward = self._data.find(to_find, cursor, start + amount - 1)
        # Look backwards for a match starting before self._read_position.
        reverse = self._data.rfind(to_find, 0, cursor + amount - 1)
        return min((forward, reverse), key=self._abs_distance)


    def search(self):
        """Figure out the longest match at the current write position.
        If there is a match of at least 2 bytes, returns a 2-tuple
        (size of match, distance to move the read position).
        Otherwise returns a tuple (0, b) where b is an int representing
        the next literal byte (so that the outer loop can skip past it).
        Either way, read and write positions are updated."""
        start = self._write_position
        best_position = self._find(2)
        if best_position == -1:
            # If we can't find at least 2 matching bytes,
            # write one byte of literal data.
            self._write_position += 1
            return 0, self._data[start]
        size = 2
        while True:
            candidate_size = size << 1
            position = self._find(candidate_size)
            if position == -1:
                break
            size, best_position = candidate_size, position
        increment = size >> 1
        while increment:
            candidate_size = size + increment
            position = self._find(candidate_size)
            if position != -1:
                size, best_position = candidate_size, position
            increment >>= 1
        # Set up for next match.
        offset = self._signed_distance(best_position)
        self._read_position = best_position + size
        self._write_position += size
        return size, offset


def make_count(value):
    if not value:
        return b'\x00'
    result = []
    while value:
        b, value = value & 0x7f, value >> 7
        result.append((b | 0x80) if value else b)
    return bytes(result)


def encode_literal(data):
    if len(data) < 3:
        return b''.join(bytes([1, b]) for b in data)
    return b'\x81' + make_count(len(data) - 3) + bytes(data)


def encode_copy(size, distance):
    if distance == 0: # single copy without move.
        return b'\x80' + make_count(size - 1)
    if size >= 0x80: # move-and-copy 0x7f, then copy-without-move the rest.
        return encode_copy(0x7f, distance) + encode_copy(size - 0x7f, 0)
    # Otherwise, create the move-and-copy.
    assert 2 <= size <= 0x7f
    first = (0x80 if distance < 0 else 0) | size
    rest = make_count(abs(distance) - 1)
    return bytes([first]) + rest


def write(out, buf):
    literal = []
    while buf.remaining:
        size, distance_or_literal = buf.search()
        if not size:
            literal.append(distance_or_literal)
        else:
            if literal:
                out.write(encode_literal(literal))
            out.write(encode_copy(size, distance_or_literal))
            literal = []
    if literal:
        out.write(encode_literal(literal))
    out.write(b'\x00')


def _write_header(out, sources):
    out.write(b'LZP')
    out.write(len(sources).to_bytes(1, 'little'))
    for s in sources:
        out.write(compute_checksum(s).to_bytes(4, 'little'))


def process(patch_name, patched_name, *source_names, header=True):
    """Create a patch.
    `patch_name` -> path to write as the patch.
    `patched_name` -> path to the patched result.
    `source_names` -> paths to input sources that will be patched.
    `header` -> whether to write a header.
    """
    names = list(source_names)
    sources = [contents(s) for s in source_names]
    with open(patch_name, 'wb') as patch:
        if header:
            _write_header(patch, sources)
        write(patch, RAMPatchBuffer(contents(patched_name), sources))
