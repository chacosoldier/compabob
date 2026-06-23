#!/usr/bin/env python3
"""modules/dictation/proxy.py — OpenAI-compatible shim for dictation cleanup.

A local dictation app (Handy, github.com/cjpais/Handy) posts its raw
speech-to-text to an OpenAI-compatible LLM post-processing endpoint. This proxy
is that endpoint. It:

- exposes `POST /v1/chat/completions` + `GET /health` on 127.0.0.1 only,
- takes the LAST user message as the transcript and ignores everything else in
  the body (so Handy's `reasoning_effort:"none"`, which some models 400 on
  — github.com/cjpais/Handy/issues/1342 — is dropped structurally),
- builds the cleanup prompt from `prompts/cleanup.md` + the rendered
  `glossary.yaml` (loaded FRESH per request so the learning loop takes effect
  without a restart; missing/empty tolerated) + the transcript,
- forwards to any OpenAI-compatible upstream (Groq by default; Ollama, OpenAI,
  or a local server all work) configured in `.env`,
- logs one `data/dictation/calls.jsonl` row per request (see README "Glossary
  format" + the row schema below),
- and NEVER blocks the paste: on upstream failure, disabled kill switch, or any
  exception it returns the raw transcript at HTTP 200 with `success:false`.

Zero non-stdlib deps except pyyaml (`pip3 install pyyaml`). Run with system
python3:  python3 modules/dictation/proxy.py

calls.jsonl row (one JSON object per line, appended on every request):
  {"ts","lang","raw","cleaned","model_used","cost_usd","duration_ms",
   "glossary_version","success"}
The `data/` dir is gitignored; it holds raw dictated text and is never committed.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import yaml

# --- Paths ------------------------------------------------------------
_HERE = Path(__file__).resolve().parent
_PROJECT_ROOT = _HERE.parent.parent  # modules/dictation -> compabob root
_ENV_FILE = _HERE / ".env"
_ENV_EXAMPLE = _HERE / ".env.example"
_PROMPT_FILE = _HERE / "prompts" / "cleanup.md"
_GLOSSARY_FILE = _HERE / "glossary.yaml"
_DATA_DIR = _PROJECT_ROOT / "data" / "dictation"
_CALLS_LOG = _DATA_DIR / "calls.jsonl"
_DEBUG_DUMP = _DATA_DIR / "debug-last-request.json"

_DEFAULTS = {
    "DICTATION_PORT": "8765",
    "DICTATION_ENABLED": "1",
    "DICTATION_DEBUG": "0",
    "DICTATION_UPSTREAM_BASE": "https://api.groq.com/openai/v1",
    "DICTATION_UPSTREAM_MODEL": "llama-3.3-70b-versatile",
    "DICTATION_UPSTREAM_KEY": "",
    "DICTATION_UPSTREAM_TIMEOUT": "30",
}


# --- Config -----------------------------------------------------------
def _load_env() -> dict:
    """Read .env.example defaults, overlay .env, then os.environ. Cheap;
    called fresh per request so the kill switch toggles without a restart."""
    cfg = dict(_DEFAULTS)
    for f in (_ENV_EXAMPLE, _ENV_FILE):
        try:
            text = f.read_text()
        except OSError:
            continue
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            cfg[k.strip()] = v.strip().strip('"').strip("'")
    for k in list(cfg):
        if k in os.environ:
            cfg[k] = os.environ[k]
    return cfg


# --- Prompt + glossary (loaded fresh per request) ---------------------
def _load_prompt() -> str:
    try:
        return _PROMPT_FILE.read_text().strip()
    except OSError:
        return "Clean up this dictation transcript. Output only the cleaned text."


def _load_glossary() -> tuple[str, int]:
    """Return (rendered prompt block, version). Tolerate missing/empty file."""
    try:
        data = yaml.safe_load(_GLOSSARY_FILE.read_text()) or {}
    except (OSError, yaml.YAMLError):
        return "", 0
    if not isinstance(data, dict):
        return "", 0
    try:
        version = int(data.get("version", 0) or 0)
    except (TypeError, ValueError):
        version = 0
    terms = data.get("terms") or []
    corrections = data.get("corrections") or []
    lines: list[str] = []
    if terms:
        lines.append("Canonical spellings (prefer these for similar-sounding words):")
        lines.extend(f"- {t}" for t in terms if t)
    if corrections:
        if lines:
            lines.append("")
        lines.append("Corrections (always apply these wrong -> right fixes):")
        for c in corrections:
            if not isinstance(c, dict):
                continue
            wrong = c.get("wrong") or []
            if isinstance(wrong, str):
                wrong = [wrong]
            right = c.get("right", "")
            if right and wrong:
                lines.append(f"- {', '.join(str(w) for w in wrong)} -> {right}")
    return "\n".join(lines), version


# --- Transcript extraction + language heuristic -----------------------
def _extract_transcript(body: dict) -> str:
    """The last user message's content. Handles string + OpenAI content-parts."""
    messages = body.get("messages") or []
    if not isinstance(messages, list):
        return ""

    def _content_to_str(content) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = []
            for p in content:
                if isinstance(p, dict) and p.get("type") == "text":
                    parts.append(p.get("text", ""))
                elif isinstance(p, str):
                    parts.append(p)
            return "".join(parts)
        return ""

    for m in reversed(messages):
        if isinstance(m, dict) and m.get("role") == "user":
            return _content_to_str(m.get("content"))
    if messages and isinstance(messages[-1], dict):
        return _content_to_str(messages[-1].get("content"))
    return ""


_ES_STOP = {"que", "de", "la", "el", "los", "las", "una", "un", "por", "con", "para",
            "pero", "muy", "esta", "como", "está", "yo", "tú", "porque", "del",
            "y", "es", "en", "se", "no", "mi", "su", "lo", "ya", "más", "ayer", "hoy"}
_DE_STOP = {"und", "der", "die", "das", "ist", "ich", "nicht", "mit", "ein", "eine",
            "auch", "für", "aber", "sich", "den", "dem", "wir", "war", "wenn",
            "habe", "hab", "noch", "schon", "gestern", "heute", "mal", "ja", "nein"}
_EN_STOP = {"the", "and", "is", "to", "of", "in", "that", "it", "you", "for",
            "with", "this", "but", "have", "was", "are", "they", "what", "at",
            "on", "my", "me", "we", "he", "she", "so", "do", "no", "not", "just",
            "like", "got", "will", "can", "a", "an", "i", "um", "yesterday", "today"}


def _detect_lang(text: str) -> str:
    """Cheap no-dep ES/DE/EN guess. 'unknown' allowed."""
    t = (text or "").lower()
    if not t.strip():
        return "unknown"
    if any(c in t for c in "ñ¿¡"):
        return "es"
    if any(c in t for c in "äöüß"):
        return "de"
    words = set(re.findall(r"[a-zà-ÿ]+", t))
    score = {"es": len(words & _ES_STOP), "de": len(words & _DE_STOP), "en": len(words & _EN_STOP)}
    best = max(score, key=lambda k: score[k])
    return best if score[best] > 0 else "unknown"


# --- Upstream call ----------------------------------------------------
def _call_upstream(messages: list[dict], cfg: dict) -> tuple[str, str, int, bool]:
    """POST to an OpenAI-compatible chat-completions endpoint.

    Returns (content, model_used, duration_ms, success). On any non-2xx,
    timeout, or empty content returns ("", "", duration, False) so the caller
    can fail open.
    """
    base = (cfg.get("DICTATION_UPSTREAM_BASE") or "").rstrip("/")
    model = cfg.get("DICTATION_UPSTREAM_MODEL") or "gpt-3.5-turbo"
    key = cfg.get("DICTATION_UPSTREAM_KEY") or ""
    try:
        timeout = float(cfg.get("DICTATION_UPSTREAM_TIMEOUT", "20"))
    except ValueError:
        timeout = 20.0
    url = f"{base}/chat/completions"
    payload = json.dumps(
        {"model": model, "messages": messages, "temperature": 0, "max_tokens": 1000, "stream": False}
    ).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    start = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read() or b"{}")
        dur = int((time.monotonic() - start) * 1000)
        content = ((data.get("choices") or [{}])[0].get("message") or {}).get("content", "") or ""
        used = data.get("model") or model
        if content.strip():
            return content.strip(), used, dur, True
        return "", "", dur, False
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        dur = int((time.monotonic() - start) * 1000)
        print(f"[dictation-proxy] upstream error: {exc}", file=sys.stderr)
        return "", "", dur, False


# --- Core cleanup -----------------------------------------------------
def _cleanup(transcript: str, cfg: dict) -> tuple[str, str, float, int, int, bool]:
    """Route the transcript through the upstream LLM.

    Returns (cleaned, model_used, cost_usd, duration_ms, glossary_version, success).
    On upstream failure returns the raw transcript with success=False (fail-open).
    cost_usd is always 0.0 — we can't price an arbitrary OpenAI-compatible upstream.
    """
    prompt_md = _load_prompt()
    glossary_block, version = _load_glossary()
    system = prompt_md
    if glossary_block:
        system = f"{prompt_md}\n\n--- GLOSSARY ---\n{glossary_block}"
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": transcript},
    ]
    content, model_used, dur, success = _call_upstream(messages, cfg)
    if success:
        return content, model_used, 0.0, dur, version, True
    # Fail-open: hand back the raw transcript, mark the row as a passthrough.
    return transcript, "passthrough", 0.0, dur, version, False


# --- Logging ----------------------------------------------------------
def _log_row(row: dict) -> None:
    try:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        with _CALLS_LOG.open("a") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    except Exception as exc:  # noqa: BLE001 — logging must never break a call
        print(f"[dictation-proxy] log write failed: {exc}", file=sys.stderr)


# --- OpenAI response shapes -------------------------------------------
def _openai_response(cleaned: str, model: str) -> dict:
    return {
        "id": "dictation-cleanup",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": cleaned},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }


def _sse_payload(cleaned: str, model: str) -> bytes:
    """Minimal OpenAI streaming response: one content delta + stop + [DONE]."""
    created = int(time.time())
    base = {
        "id": "dictation-cleanup",
        "object": "chat.completion.chunk",
        "created": created,
        "model": model,
    }
    first = {
        **base,
        "choices": [{"index": 0, "delta": {"role": "assistant", "content": cleaned}, "finish_reason": None}],
    }
    last = {**base, "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]}
    out = (
        f"data: {json.dumps(first, ensure_ascii=False)}\n\n"
        f"data: {json.dumps(last, ensure_ascii=False)}\n\n"
        "data: [DONE]\n\n"
    )
    return out.encode("utf-8")


# --- HTTP handler -----------------------------------------------------
class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_args):  # silence default per-request access logs
        pass

    def _send_json(self, code: int, obj: dict) -> None:
        payload = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _respond(self, cleaned: str, model: str, stream: bool) -> None:
        if stream:
            payload = _sse_payload(cleaned, model)
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        else:
            self._send_json(200, _openai_response(cleaned, model))

    def do_GET(self):  # noqa: N802 — stdlib naming
        if self.path.rstrip("/") == "/health":
            self._send_json(200, {"status": "ok"})
        else:
            self._send_json(404, {"error": "not found"})

    def do_POST(self):  # noqa: N802 — stdlib naming
        # Parse the body defensively; a bad body must still fail open.
        body: dict = {}
        try:
            length = int(self.headers.get("Content-Length") or 0)
            body_bytes = self.rfile.read(length) if length else b""
            body = json.loads(body_bytes or b"{}")
            if not isinstance(body, dict):
                body = {}
        except Exception:  # noqa: BLE001
            body = {}

        raw_transcript = ""
        stream = bool(body.get("stream"))
        try:
            cfg = _load_env()
            if cfg.get("DICTATION_DEBUG", "0") == "1":
                try:
                    _DATA_DIR.mkdir(parents=True, exist_ok=True)
                    _DEBUG_DUMP.write_text(json.dumps(body, ensure_ascii=False, indent=2))
                except Exception:  # noqa: BLE001
                    pass

            raw_transcript = _extract_transcript(body)
            enabled = cfg.get("DICTATION_ENABLED", "1") != "0"

            if not enabled:
                _, version = _load_glossary()
                cleaned, model_used, cost, dur, success = (raw_transcript, "passthrough", 0.0, 0, False)
            else:
                cleaned, model_used, cost, dur, version, success = _cleanup(raw_transcript, cfg)

            _log_row(
                {
                    "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
                    "lang": _detect_lang(raw_transcript),
                    "raw": raw_transcript,
                    "cleaned": cleaned,
                    "model_used": model_used,
                    "cost_usd": cost,
                    "duration_ms": dur,
                    "glossary_version": version,
                    "success": success,
                }
            )
            self._respond(cleaned, model_used, stream)
        except Exception as exc:  # noqa: BLE001 — last-resort fail-open
            print(f"[dictation-proxy] handler error: {exc}", file=sys.stderr)
            try:
                self._respond(raw_transcript, "passthrough", stream)
            except Exception:  # noqa: BLE001
                pass


def main() -> None:
    cfg = _load_env()
    try:
        port = int(cfg.get("DICTATION_PORT", "8765"))
    except ValueError:
        port = 8765
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"[dictation-proxy] listening on http://127.0.0.1:{port}", file=sys.stderr)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == "__main__":
    main()
