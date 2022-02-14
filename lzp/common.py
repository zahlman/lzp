from zlib import adler32 as compute_checksum


def contents(filename):
    with open(filename, 'rb') as f:
        return f.read()

