from os import chdir

from pytest import fixture, raises

from lzp import __version__
from lzp.decode import number, process, RAMPatchStream


FILES = {
    'count_251.bin': (
        "00 01 02 03 04 05 06 07 08 09 0A 0B 0C 0D 0E 0F",
        "10 11 12 13 14 15 16 17 18 19 1A 1B 1C 1D 1E 1F",
        "20 21 22 23 24 25 26 27 28 29 2A 2B 2C 2D 2E 2F",
        "30 31 32 33 34 35 36 37 38 39 3A 3B 3C 3D 3E 3F",
        "40 41 42 43 44 45 46 47 48 49 4A 4B 4C 4D 4E 4F",
        "50 51 52 53 54 55 56 57 58 59 5A 5B 5C 5D 5E 5F",
        "60 61 62 63 64 65 66 67 68 69 6A 6B 6C 6D 6E 6F",
        "70 71 72 73 74 75 76 77 78 79 7A 7B 7C 7D 7E 7F",
        "80 81 82 83 84 85 86 87 88 89 8A 8B 8C 8D 8E 8F",
        "90 91 92 93 94 95 96 97 98 99 9A 9B 9C 9D 9E 9F",
        "A0 A1 A2 A3 A4 A5 A6 A7 A8 A9 AA AB AC AD AE AF",
        "B0 B1 B2 B3 B4 B5 B6 B7 B8 B9 BA BB BC BD BE BF",
        "C0 C1 C2 C3 C4 C5 C6 C7 C8 C9 CA CB CC CD CE CF",
        "D0 D1 D2 D3 D4 D5 D6 D7 D8 D9 DA DB DC DD DE DF",
        "E0 E1 E2 E3 E4 E5 E6 E7 E8 E9 EA EB EC ED EE EF",
        "F0 F1 F2 F3 F4 F5 F6 F7 F8 F9 FA"
    ),
    # the corresponding value is equivalent to 104 (modulo 251).
    # When used for movement, we therefore move 105 steps.
    'bignum_8.bin': ("80 81 82 83 84 85 86 87",),
    'forward_17.bin': (
        "4C 5A 50 01", # LZP 1 source
        "3A 3F 7A 90", # checksum for count_251
        "02 80 81 82 83 84 85 86 87" # forward that many bytes and copy 2
    ),
    'fresult_2.bin': ("69 6A",),
    'backward_17.bin': (
        "4C 5A 50 01", # LZP 1 source
        "3A 3F 7A 90", # checksum for count_251
        "82 80 81 82 83 84 85 86 87" # forward that many bytes and copy 2
    ),
    'bresult_2.bin': ("92 93",),
}


@fixture
def setup_dir(tmp_path):
    for name, data in FILES.items():
        _, _, count = name.partition('_')
        count, _, _ = count.partition('.')
        data = bytes.fromhex(' '.join(data))
        assert len(data) == int(count)
        (tmp_path / name).write_bytes(data)
    chdir(tmp_path)


def _check_equal_files(a, b):
    with open(a, 'rb') as f:
        ad = f.read()
    with open(b, 'rb') as f:
        bd = f.read()
    assert ad == bd


def test_make_stream(setup_dir):
    RAMPatchStream(('count_251.bin',), (977238672,))
    with raises(ValueError):
        RAMPatchStream(('count_251.bin',), (0,))


def test_big_number(setup_dir):
    patcher = RAMPatchStream(('count_251.bin',), (977238672,))
    with open('bignum_8.bin', 'rb') as f:
        assert number(f, 0) == 0xe182840608080


def test_wrong_file(setup_dir):
    with raises(ValueError):
        process('forward_17.bin', 'out.bin')
    with raises(ValueError):
        process('forward_17.bin', 'out.bin', 'count_251.bin', 'count_251.bin')
    with raises(ValueError):
        process('forward_17.bin', 'out.bin', 'forward_17.bin')


def test_forward(setup_dir):
    process('forward_17.bin', 'out.bin', 'count_251.bin')
    _check_equal_files('out.bin', 'fresult_2.bin')


def test_forward(setup_dir):
    process('backward_17.bin', 'out.bin', 'count_251.bin')
    _check_equal_files('out.bin', 'bresult_2.bin')


def test_version():
    assert __version__ == '0.1.0'
