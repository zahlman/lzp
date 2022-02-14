from zlib import adler32 as compute_checksum


__version__ = '0.1.0'


def contents(filename):
    with open(filename, 'rb') as f:
        return f.read()
