# Module: Transcribe (local recording + transcription)

One hotkey records a call; the next one stops it, transcribes it **on your
machine**, copies the text to your clipboard, and files a markdown transcript
into `vault/raw/meetings/`. No cloud transcription service, no API key, no audio
ever leaving your laptop.

**Highly encouraged.** Most of what your assistant is worth comes from context,
and most of your context is spoken: standups, sales calls, 1:1s, the hallway
decision nobody wrote down. This module turns every call into searchable,
linkable text your assistant can read, with effectively zero friction and zero
privacy cost. It is opt-in like everything else here, but it is the single
cheapest way to widen what your assistant actually knows about your week.

## How it works

A toggle script (`record.py`) drives `ffmpeg` to capture audio, then
`mlx-whisper` (Whisper running locally on Apple Silicon) to transcribe it:

- **First run** starts recording in the background.
- **Second run** stops it, transcribes, copies the text to your clipboard, and
  writes `vault/raw/meetings/<date>-<HH-MM>-[title-]call.md` with frontmatter
  (date, duration, language, model, word count). Your notes or wiki pipeline
  picks the file up from there.

Capturing **both sides of a call** is the point, so the default device is an
**aggregate device** (your mic + system audio mixed). You record what they say,
not just what you say.

## Prerequisites (all local)

```bash
brew install blackhole-2ch     # virtual audio device (captures system audio)
brew install ffmpeg            # recording
pip3 install mlx-whisper       # local transcription (Apple Silicon)
```

Then, once, in **Audio MIDI Setup** (macOS):

1. Create a **Multi-Output Device** = your speakers + **BlackHole 2ch**, so you
   still hear the call while it is captured.
2. Create an **Aggregate Device** = your microphone + **BlackHole 2ch**, so the
   recording contains both sides.

Device names differ per machine. List yours and confirm the mapping:

```bash
python3 modules/transcribe/record.py devices
```

If a name differs from the defaults, override it (e.g. in your shell profile):

```bash
export TRANSCRIBE_DEVICE_AGGREGATE="Aggregate Device"
export TRANSCRIBE_DEVICE_MIC="MacBook Pro Microphone"
export TRANSCRIBE_DEVICE_BLACKHOLE="BlackHole 2ch"
```

## Use it

```bash
# Toggle: start, then run again to stop + transcribe (both sides of the call)
python3 modules/transcribe/record.py

# Mic only
python3 modules/transcribe/record.py --device mic

# Name the file
python3 modules/transcribe/record.py --title acme-discovery

# Higher accuracy (slower)
python3 modules/transcribe/record.py --model medium-mlx

# Is it recording right now?
python3 modules/transcribe/record.py --status
```

The transcript lands in `vault/raw/meetings/` (override with `--out`) and is
already on your clipboard, so you can paste it straight into a note or a chat
with your assistant.

## Optional: bind it to a hotkey

Running a command twice is the whole interface, which makes it a natural fit for
a global hotkey. With [Hammerspoon](https://www.hammerspoon.org), one key both
starts and stops because the script toggles:

```lua
-- ~/.hammerspoon/init.lua
hs.hotkey.bind({"ctrl", "shift"}, "R", function()
  hs.task.new("/usr/bin/python3",
    nil,
    {os.getenv("HOME") .. "/compabob/modules/transcribe/record.py"}
  ):start()
end)
```

Any launcher that can run a shell command (Raycast, Alfred, Karabiner, a
Shortcut) works the same way; the script does the start/stop bookkeeping.

## Enable it

1. Run the prerequisites and the one-time Audio MIDI Setup above.
2. Set `transcribe: true` in `config/user.config.yaml` so `/system-audit` knows
   to check it.

## Known issues

- **Stop didn't fire cleanly.** If the toggle never reaches the stop call (an app
  switch ate the hotkey, say), a raw `.wav` is left in `.tmp/`. Just run
  `record.py` again: it detects the in-progress recording and stops + transcribes
  it.
- **Don't run two transcriptions at once.** Parallel `mlx-whisper` processes
  contend for the GPU and all crawl. Sequential is several times faster; let one
  finish before starting the next.
- **Apple Silicon only** for the local model path (`mlx-whisper`). On Intel,
  swap in `openai-whisper` and point `MODELS` at a CPU model.

## A note on privacy

Recording and transcription both happen on your machine; the audio and the text
never touch a network. The transcript is a plain markdown file in your vault,
which is git-ignored by default. Treat call recordings as the sensitive material
they are, and check the consent rules where you live before recording anyone.
