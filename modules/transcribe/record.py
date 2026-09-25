#!/usr/bin/env python3
"""
One-click audio recording + local transcription. Fully offline.

Toggle model: first run starts recording, second run stops, transcribes with
mlx-whisper, copies the text to your clipboard, and drops a markdown transcript
into vault/raw/meetings/ where your notes pipeline can pick it up.

Usage:
    python3 modules/transcribe/record.py              # Toggle (start/stop)
    python3 modules/transcribe/record.py --device mic # Mic only
    python3 modules/transcribe/record.py --status     # Check if recording
    python3 modules/transcribe/record.py devices      # List audio devices (setup)
    python3 modules/transcribe/record.py --model medium-mlx  # Higher accuracy
    python3 modules/transcribe/record.py --title acme-call   # Slug the filename

Prerequisites (all local, no API keys):
    - BlackHole 2ch installed              (brew install blackhole-2ch)
    - A Multi-Output / Aggregate device    (macOS Audio MIDI Setup)
    - ffmpeg                               (brew install ffmpeg)
    - mlx-whisper in modules/transcribe/.venv (see README; this script re-runs
      itself with that venv's python when it exists)

Device names vary per machine. Run `record.py devices` to see yours, then
override any of these via environment variable if they differ from the defaults:
    TRANSCRIBE_DEVICE_BLACKHOLE  (default "BlackHole 2ch")
    TRANSCRIBE_DEVICE_AGGREGATE  (default "Aggregate Device")
    TRANSCRIBE_DEVICE_MIC        (default "MacBook Pro Microphone")
"""

import argparse
import json
import os
import re
import signal
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent.parent
TMP = PROJECT / ".tmp"
PID_FILE = TMP / "recording.pid"
META_FILE = TMP / "recording.meta"
DEFAULT_INBOX = PROJECT / "vault" / "raw" / "meetings"

MODELS = {
    "small-mlx": "mlx-community/whisper-small-mlx",
    "medium-mlx": "mlx-community/whisper-medium-mlx",
}
DEFAULT_MODEL = "small-mlx"
DEFAULT_DEVICE = "aggregate"  # Both sides of a call (system audio + mic)

# Names are machine-specific; override via env (see module docstring).
DEVICE_NAMES = {
    "blackhole": os.environ.get("TRANSCRIBE_DEVICE_BLACKHOLE", "BlackHole 2ch"),
    "aggregate": os.environ.get("TRANSCRIBE_DEVICE_AGGREGATE", "Aggregate Device"),
    "mic": os.environ.get("TRANSCRIBE_DEVICE_MIC", "MacBook Pro Microphone"),
}


def notify(title: str, message: str):
    """Send a macOS notification (no-op-safe on other platforms)."""
    subprocess.run(
        ["osascript", "-e", f'display notification "{message}" with title "{title}"'],
        capture_output=True,
    )


def list_audio_devices() -> str:
    """Return ffmpeg's avfoundation audio-device listing (stderr)."""
    result = subprocess.run(
        ["ffmpeg", "-f", "avfoundation", "-list_devices", "true", "-i", ""],
        capture_output=True, text=True,
    )
    return result.stderr


def print_devices():
    """Print available audio input devices to help with first-time setup."""
    output = list_audio_devices()
    print("Available audio devices:")
    in_audio = False
    for line in output.splitlines():
        if "audio devices" in line.lower():
            in_audio = True
            continue
        if in_audio and "[" in line:
            print(f"  {line.strip()}")
    print("\nCurrent device-name mapping (override with TRANSCRIBE_DEVICE_* env vars):")
    for key, name in DEVICE_NAMES.items():
        print(f"  {key:<10} -> {name!r}")


def resolve_device_index(device_key: str) -> str:
    """Resolve a device key to its ffmpeg AVFoundation audio index."""
    target_name = DEVICE_NAMES.get(device_key)
    if not target_name:
        print(f"Unknown device: {device_key}", file=sys.stderr)
        sys.exit(1)

    output = list_audio_devices()
    in_audio = False
    for line in output.splitlines():
        if "audio devices" in line.lower():
            in_audio = True
            continue
        if in_audio:
            match = re.search(r"\[(\d+)\]\s+(.+)$", line)
            if match:
                idx, name = match.group(1), match.group(2).strip()
                if name == target_name:
                    return f":{idx}"

    print(f"Device '{target_name}' not found. Is it connected?", file=sys.stderr)
    print("Run `record.py devices` to see available devices, then set the matching "
          "TRANSCRIBE_DEVICE_* env var.", file=sys.stderr)
    sys.exit(1)


def start_recording(device: str, model_key: str, title: str, inbox: Path):
    """Start ffmpeg recording in the background."""
    TMP.mkdir(parents=True, exist_ok=True)
    inbox.mkdir(parents=True, exist_ok=True)

    device_index = resolve_device_index(device)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    wav_path = TMP / f"recording_{timestamp}.wav"

    proc = subprocess.Popen(
        [
            "ffmpeg", "-f", "avfoundation",
            "-i", device_index,
            "-ar", "16000", "-ac", "1",
            "-acodec", "pcm_s16le",
            "-y", str(wav_path),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    meta = {
        "pid": proc.pid,
        "path": str(wav_path),
        "started": datetime.now().isoformat(),
        "device": device,
        "model": model_key,
        "title": title.strip(),
        "inbox": str(inbox),
    }
    PID_FILE.write_text(str(proc.pid))
    META_FILE.write_text(json.dumps(meta))

    notify("Recording", f"Started ({device})")
    title_note = f", title: {title}" if title else ""
    print(f"Recording started (PID {proc.pid}, device: {device}{title_note})")


def stop_and_transcribe():
    """Stop recording, transcribe locally, copy to clipboard, write a note."""
    meta = json.loads(META_FILE.read_text())
    pid = meta["pid"]
    wav_path = Path(meta["path"])
    model_key = meta.get("model", DEFAULT_MODEL)
    model_repo = MODELS.get(model_key, MODELS[DEFAULT_MODEL])
    inbox = Path(meta.get("inbox", DEFAULT_INBOX))

    # Graceful stop (let ffmpeg finalize the wav container).
    try:
        os.kill(pid, signal.SIGINT)
        for _ in range(20):
            time.sleep(0.25)
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                break
    except ProcessLookupError:
        pass

    PID_FILE.unlink(missing_ok=True)
    META_FILE.unlink(missing_ok=True)

    if not wav_path.exists() or wav_path.stat().st_size < 1000:
        notify("Recording", "No audio captured (file too small)")
        print("No audio captured.", file=sys.stderr)
        return

    started = datetime.fromisoformat(meta["started"])
    duration_s = (datetime.now() - started).total_seconds()

    notify("Transcribing", f"Processing {int(duration_s)}s of audio...")
    print(f"Transcribing ({int(duration_s)}s, model: {model_key})...")

    import mlx_whisper
    result = mlx_whisper.transcribe(str(wav_path), path_or_hf_repo=model_repo)
    text = result.get("text", "").strip()
    language = result.get("language", "unknown")

    if not text:
        notify("Transcription", "No speech detected")
        print("No speech detected.", file=sys.stderr)
        return

    subprocess.run(["pbcopy"], input=text.encode(), check=True)

    timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M")
    title_slug = meta.get("title", "").strip()
    if title_slug:
        output = inbox / f"{timestamp}-{title_slug}-call.md"
    else:
        output = inbox / f"{timestamp}-call.md"
    word_count = len(text.split())
    output.write_text(
        f"---\n"
        f"type: transcript\n"
        f"date: {datetime.now().strftime('%Y-%m-%d')}\n"
        f"duration: {int(duration_s)}s\n"
        f"language: {language}\n"
        f"device: {meta['device']}\n"
        f"model: {model_key}\n"
        f"words: {word_count}\n"
        f"---\n\n"
        f"{text}\n"
    )

    notify("Transcript Ready",
           f"{word_count} words, {int(duration_s/60)}m{int(duration_s%60):02d}s. Copied to clipboard.")
    print(f"Done. {word_count} words, language: {language}")
    print(f"Saved: {output}")
    print("Copied to clipboard.")


def show_status():
    """Show the current recording status."""
    if not PID_FILE.exists():
        print("Not recording.")
        return

    meta = json.loads(META_FILE.read_text())
    started = datetime.fromisoformat(meta["started"])
    elapsed = (datetime.now() - started).total_seconds()
    pid = meta["pid"]

    try:
        os.kill(pid, 0)
        print(f"Recording: {int(elapsed)}s on {meta['device']} (PID {pid})")
    except ProcessLookupError:
        print("Stale recording state (process dead). Cleaning up.")
        PID_FILE.unlink(missing_ok=True)
        META_FILE.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description="One-click local record + transcribe")
    parser.add_argument("action", nargs="?", default="toggle",
                        choices=["start", "stop", "toggle", "status", "devices"],
                        help="start, stop, toggle (default), status, or devices")
    parser.add_argument("--device", default=DEFAULT_DEVICE,
                        choices=list(DEVICE_NAMES.keys()),
                        help="Audio device (default: aggregate = both sides of a call)")
    parser.add_argument("--model", default=DEFAULT_MODEL,
                        choices=list(MODELS.keys()),
                        help="Whisper model (default: small-mlx)")
    parser.add_argument("--title", default="",
                        help="Slug for the filename, e.g. 'acme-call'. "
                             "Used as: vault/raw/meetings/<date>-<HH-MM>-<title>-call.md")
    parser.add_argument("--out", default=str(DEFAULT_INBOX),
                        help="Output directory for the transcript note "
                             "(default: vault/raw/meetings/)")
    args = parser.parse_args()

    inbox = Path(args.out)

    if args.action == "devices":
        print_devices()
    elif args.action == "status":
        show_status()
    elif args.action == "start":
        if PID_FILE.exists():
            print("Already recording. Use 'stop' first.", file=sys.stderr)
        else:
            start_recording(args.device, args.model, args.title, inbox)
    elif args.action == "stop":
        if PID_FILE.exists():
            stop_and_transcribe()
        else:
            print("Not recording.", file=sys.stderr)
    else:  # toggle
        if PID_FILE.exists():
            stop_and_transcribe()
        else:
            start_recording(args.device, args.model, args.title, inbox)


def _reexec_in_module_venv():
    """Re-run with modules/transcribe/.venv's python if it exists and we are not it.

    mlx-whisper lives in that venv (Homebrew Python refuses a global pip install),
    so a hotkey or a bare `python3 record.py` still finds it.
    """
    venv_py = Path(__file__).resolve().parent / ".venv" / "bin" / "python"
    if venv_py.exists() and Path(sys.prefix).resolve() != venv_py.parent.parent.resolve():
        os.execv(str(venv_py), [str(venv_py), str(Path(__file__).resolve()), *sys.argv[1:]])


if __name__ == "__main__":
    _reexec_in_module_venv()
    main()
