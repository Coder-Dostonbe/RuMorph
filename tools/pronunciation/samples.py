"""Voice samples for choosing a pronunciation voice (temporary, not part of the app).

Writes samples/<voice>/<NN>-<word>.mp3 for the same words in every candidate voice:
- Vosk TTS ru multi (Apache-2.0), every speaker;
- utrobinmv/tts_ru_free_hf_vits_high_multispeaker (Apache-2.0), every speaker;
- the current Commons recordings (mixed speakers) for comparison.
"""
import json
import subprocess
import sys
import urllib.parse
import urllib.error
import urllib.request
import time
from pathlib import Path

WORDS = ["книга", "молоко", "хорошо", "говорить", "девушка", "магазин", "звонить", "позвонить",
         "вода", "город", "автобус", "спасибо"]
OUT = Path("samples")
AGENT = "ZabonPronunciations/1.0 (https://github.com/Coder-Dostonbe/RuMorph)"


def mp3(wav: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(wav), "-ac", "1", "-b:a", "64k", str(target)],
                   check=True)
    wav.unlink()


def vosk() -> None:
    from vosk_tts import Model, Synth
    model = Model(model_name="vosk-model-tts-ru-0.9-multi")
    synth = Synth(model)
    for speaker in range(12):
        try:
            for n, word in enumerate(WORDS, 1):
                wav = Path(f"/tmp/v{speaker}.wav")
                synth.synth(word, str(wav), speaker_id=speaker)
                mp3(wav, OUT / f"vosk-speaker{speaker}" / f"{n:02d}-{word}.mp3")
        except Exception as exc:  # noqa: BLE001
            print(f"vosk speaker {speaker}: stop ({exc!r})")
            break
        print(f"vosk speaker {speaker}: ok")


def utrobin() -> None:
    import scipy.io.wavfile
    import torch
    from transformers import AutoTokenizer, VitsModel
    name = "utrobinmv/tts_ru_free_hf_vits_high_multispeaker"
    model = VitsModel.from_pretrained(name).eval()
    tokenizer = AutoTokenizer.from_pretrained(name)
    for speaker in range(getattr(model.config, "num_speakers", 1) or 1):
        for n, word in enumerate(WORDS, 1):
            inputs = tokenizer(word.lower(), return_tensors="pt")
            with torch.no_grad():
                audio = model(**inputs, speaker_id=speaker).waveform[0].numpy()
            wav = Path(f"/tmp/u{speaker}.wav")
            scipy.io.wavfile.write(wav, rate=model.config.sampling_rate, data=audio)
            mp3(wav, OUT / f"utrobin-speaker{speaker}" / f"{n:02d}-{word}.mp3")
        print(f"utrobin speaker {speaker}: ok")


def commons() -> None:
    words = json.loads(Path("apps/client/src/data/pronunciations.json").read_text(encoding="utf-8"))["words"]
    for n, word in enumerate(WORDS, 1):
        entry = words.get(word)
        if not entry:
            continue
        url = "https://upload.wikimedia.org/wikipedia/commons/" + urllib.parse.quote(entry["path"], safe="/()_-.,~!*'")
        request = urllib.request.Request(url, headers={"User-Agent": AGENT})
        target = OUT / "commons-hozirgi" / f"{n:02d}-{word} ({entry['author'][:30]}).mp3"
        target.parent.mkdir(parents=True, exist_ok=True)
        for attempt in range(6):
            try:
                target.write_bytes(urllib.request.urlopen(request, timeout=60).read())
                break
            except urllib.error.HTTPError as exc:
                if exc.code != 429:
                    raise
                time.sleep(20 * (attempt + 1))
        time.sleep(3)
    print("commons: ok")


{"vosk": vosk, "utrobin": utrobin, "commons": commons}[sys.argv[1]]()
