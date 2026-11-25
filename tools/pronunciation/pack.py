"""Builds a voice pack the app downloads once: every word's pronunciation in one file.

    python tools/pronunciation/pack.py vosk --speaker 2 --id vosk-f2 --out zabon-voice-vosk-f2-1.bin
    python tools/pronunciation/pack.py read zabon-voice-vosk-f2-1.bin     # check and describe

`vosk`: every lexicon word (stress homographs excepted, see build.py) synthesised with Vosk TTS
(vosk-model-tts-ru-0.9-multi, Apache-2.0; voices chosen by the project owner, docs/DECISIONS.md),
then trimmed, levelled and encoded as Ogg Opus. It also writes <out>.sample.ogg, a short
phrase the app plays before the pack is downloaded, and <out>.json, the pack's entry for
apps/client/src/data/voicePacks.json.

File format (version 1):
    b"ZVP1" | header length (uint32, big-endian) | header (UTF-8 JSON) | audio data
    header = {"format": "zabon-voice-pack", "version": 1, "mime": ..., "voice": {...},
              "words": {word: [offset, length, author, license], ...}}
Offsets count from the start of the audio data. Each word's audio is a complete Ogg Opus file.

Needs ffmpeg with libopus (and the vosk-tts package for `vosk`).
"""

from __future__ import annotations

import argparse
import json
import re
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import build  # noqa: E402

MAGIC = b"ZVP1"
FORMAT = "zabon-voice-pack"
VERSION = 1
MIME = "audio/ogg; codecs=opus"
MAX_WORD_BYTES = 200_000

# Trim silence at both ends, even out loudness, Opus 32 kbit/s mono: about 4-8 KB a word.
FILTER = ("silenceremove=start_periods=1:start_threshold=-50dB:start_silence=0.05,"
          "areverse,silenceremove=start_periods=1:start_threshold=-50dB:start_silence=0.08,areverse,"
          "loudnorm=I=-18:TP=-2:LRA=7")


def write_pack(path: Path, voice: dict, items: list[tuple[str, bytes, str, str]]) -> None:
    """items: (word, ogg opus bytes, author, license)."""
    words: dict[str, list] = {}
    offset = 0
    for word, data, author, license in items:
        words[word] = [offset, len(data), author, license]
        offset += len(data)
    header = json.dumps({"format": FORMAT, "version": VERSION, "mime": MIME, "voice": voice, "words": words},
                        ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    with path.open("wb") as out:
        out.write(MAGIC + struct.pack(">I", len(header)) + header)
        for _, data, _, _ in items:
            out.write(data)


def read_pack(path: Path) -> tuple[dict, bytes]:
    blob = path.read_bytes()
    if blob[:4] != MAGIC:
        raise build.BuildError("not a voice pack")
    (size,) = struct.unpack(">I", blob[4:8])
    header = json.loads(blob[8:8 + size].decode("utf-8"))
    data = blob[8 + size:]
    if header.get("format") != FORMAT or header.get("version") != VERSION:
        raise build.BuildError("unknown voice pack version")
    for word, (offset, length, author, license) in header["words"].items():
        if offset < 0 or length <= 0 or offset + length > len(data) or length > MAX_WORD_BYTES:
            raise build.BuildError(f"{word}: bad range")
        if data[offset:offset + 4] != b"OggS":
            raise build.BuildError(f"{word}: not an Ogg file")
        if not author or not license:
            raise build.BuildError(f"{word}: no credit")
    return header, data


def to_opus(source: bytes) -> bytes:
    with tempfile.TemporaryDirectory() as tmp:
        src, dst = Path(tmp) / "in", Path(tmp) / "out.ogg"
        src.write_bytes(source)
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(src), "-af", FILTER, "-ac", "1",
                        "-ar", "24000", "-c:a", "libopus", "-b:a", "32k", "-application", "voip",
                        "-map_metadata", "-1", str(dst)], check=True)
        return dst.read_bytes()


MODEL = "vosk-model-tts-ru-0.9-multi"
SAMPLE = "Здравствуйте! Книга, молоко, спасибо."


def vosk(speaker: int, voice_id: str, out: Path) -> None:
    import hashlib

    from vosk_tts import Model, Synth

    synth = Synth(Model(model_name=MODEL))
    words = [w for w in build.lexicon_words() if w not in build.HOMOGRAPHS]
    credit = f"Vosk TTS ({MODEL})"

    def speak(text: str) -> bytes:
        with tempfile.TemporaryDirectory() as tmp:
            wav = Path(tmp) / "a.wav"
            synth.synth(text, str(wav), speaker_id=speaker)
            return to_opus(wav.read_bytes())

    items = []
    for n, word in enumerate(words, 1):
        items.append((word, speak(word), credit, "Apache-2.0"))
        if n % 250 == 0:
            print(f"  {voice_id}: {n}/{len(words)}", file=sys.stderr)
    voice = {"id": voice_id, "engine": "Vosk TTS", "model": MODEL, "speaker": speaker, "license": "Apache-2.0"}
    write_pack(out, voice, items)
    header, data = read_pack(out)
    out.with_suffix(".sample.ogg").write_bytes(speak(SAMPLE))
    entry = {"id": voice_id, "file": out.name, "bytes": out.stat().st_size, "words": len(header["words"]),
             "sha256": hashlib.sha256(out.read_bytes()).hexdigest()}
    out.with_suffix(".json").write_text(json.dumps(entry, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {out}: {len(header['words'])} words, {len(data) / 1e6:.1f} MB audio")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("command", choices=["vosk", "read"])
    parser.add_argument("path", nargs="?", type=Path)
    parser.add_argument("--out", type=Path, default=Path("zabon-voice.bin"))
    parser.add_argument("--speaker", type=int, default=0)
    parser.add_argument("--id", default="vosk")
    args = parser.parse_args()
    try:
        if args.command == "vosk":
            if not re.fullmatch(r"[a-z0-9-]{1,40}", args.id):
                raise build.BuildError("--id: lower-case letters, digits and '-'")
            vosk(args.speaker, args.id, args.out)
        else:
            header, data = read_pack(args.path)
            print(json.dumps(header["voice"], ensure_ascii=False), len(header["words"]), "words,", len(data), "bytes")
    except build.BuildError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
