# standard library
from os import chdir
# test framework
from pytest import fixture, mark, raises
parametrize = mark.parametrize
del mark
# current package
from lzp import __version__, do_decode, do_encode
from lzp.decode import number, RAMPatchStream


def test_version():
    assert __version__ == '0.1.0'


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
    # Example patch files, to test header-check and commands.
    'header_8.bin': (
        "4C 5A 50 01", # LZP 1 source
        "3A 3F 7A 90" # checksum for count_251
    ),
    'forward_10.bin': (
        # forward 0xe182840608080 + 1 bytes, then copy 2
        # that is equivalent to 105 (modulo 251).
        "02 80 81 82 83 84 85 86 07 00", # forward that many bytes and copy 2
    ),
    'fresult_2.bin': ("69 6A",),
    'backward_10.bin': (
        # backward 0xe182840608080 + 1 bytes, then copy 2
        # that is equivalent to 105 (modulo 251).
        "82 80 81 82 83 84 85 86 07 00", # forward that many bytes and copy 2
    ),
    'bresult_2.bin': ("92 93",),
    'earlyend_10.bin': (
        "00 82 80 81 82 83 84 85 86 07", # end of stream before command
    ),
    'eresult_0.bin': (),
    'blockcopy_4.bin': ("80 FA 01 00",), # copy 250+1 bytes, then done
    # copy three literal bytes one at a time
    'copysingle_7.bin': ("01 4C 01 5A 01 50 00",),
    # copy three bytes
    'copybatch_6.bin': ("81 00 4C 5A 50 00",),
    # either way, this should be the result
    'firstthree_3.bin': ("4C 5A 50",),
    # Patch resulting from trying to compress count_251.bin
    'patch_259.bin': (
        "4C 5A 50 00", # LZP, no sources
        "81 F8 01", # copy 248 + 3 literal bytes
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
        "F0 F1 F2 F3 F4 F5 F6 F7 F8 F9 FA",
        "00" # required end of stream
    ),
    # Something that *does* compress.
    'mostlyzero_251.bin': ("00 " * 250 + "01",),
    'zeropatch_12.bin': (
        "4C 5A 50 00", # LZP, no sources
        "01 00", # write a zero
        "80 F8 01", # copy 248+1 bytes without moving
        "01 01", # write a 1
        "00" # end of stream
    )
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


def test_wrong_file(setup_dir):
    with raises(ValueError):
        do_decode('header_8.bin', 'out.bin')
    with raises(ValueError):
        do_decode('header_8.bin', 'out.bin', 'count_251.bin', 'count_251.bin')
    with raises(ValueError):
        do_decode('header_8.bin', 'out.bin', 'forward_10.bin')


@parametrize("patch,expected", (
    # move forward command
    ('forward_10.bin', 'fresult_2.bin'),
    # move backward command
    ('backward_10.bin', 'bresult_2.bin'),
    # end command not at end of file
    ('earlyend_10.bin', 'eresult_0.bin'),
    # block copy
    ('blockcopy_4.bin', 'count_251.bin'),
    # 3 literal bytes, one at a time
    ('copysingle_7.bin', 'firstthree_3.bin'),
    # 3 literal bytes, as a group
    ('copybatch_6.bin', 'firstthree_3.bin')
))
def test_apply(setup_dir, patch, expected):
    do_decode(patch, 'out.bin', 'count_251.bin', header=False)
    _check_equal_files('out.bin', expected)


# test making patches from zero sources (compressing the desired output)
@parametrize("source,expected", (
    ('count_251.bin', 'patch_259.bin'),
    ('mostlyzero_251.bin', 'zeropatch_12.bin')
))
def test_compress(setup_dir, source, expected):
    do_encode('out.bin', source)
    _check_equal_files('out.bin', expected)
