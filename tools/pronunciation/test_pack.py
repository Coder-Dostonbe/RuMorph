import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import build  # noqa: E402
import pack  # noqa: E402


def ogg(tag: bytes) -> bytes:
    return b"OggS" + tag


def test_round_trip(tmp_path):
    path = tmp_path / "v.bin"
    pack.write_pack(path, {"id": "t"}, [("дом", ogg(b"1"), "X", "CC0"), ("книга", ogg(b"22"), "Y", "CC BY 4.0")])
    header, data = pack.read_pack(path)
    assert header["voice"] == {"id": "t"}
    offset, length, author, license = header["words"]["книга"]
    assert data[offset:offset + length] == ogg(b"22") and (author, license) == ("Y", "CC BY 4.0")


def test_bad_files_are_refused(tmp_path):
    path = tmp_path / "v.bin"
    path.write_bytes(b"NOPE")
    with pytest.raises(build.BuildError):
        pack.read_pack(path)
    pack.write_pack(path, {"id": "t"}, [("дом", b"RIFF....", "X", "CC0")])
    with pytest.raises(build.BuildError):
        pack.read_pack(path)


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="needs ffmpeg")
def test_opus_conversion(tmp_path):
    wav = tmp_path / "a.wav"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
                    str(wav)], check=True)
    data = pack.to_opus(wav.read_bytes())
    assert data[:4] == b"OggS" and b"OpusHead" in data[:200]
