# AGENTS.md — robot_yanshee

Onboard UBTECH Yanshee scripts (run on the robot's Raspberry Pi, Debian). No build, tests, lint, or CI.

## Entry points
- `yanshee_detect_any.py` — current/main. Gesture-gated loop: `gesture_control_loop()` (thumbsup → `main_loop_interactive()` → `random_dance(interactive=True)`). Uses onboard mic/TTS via `YanAPI.sync_do_voice_iat_value()` / `sync_do_tts()`. Only stdlib deps (`json`, `urllib`, `time`, `random`) + `YanAPI`.
- `yanshee_detect.py` — legacy/off-robot variant. Local mic via `pyaudio`, STT via Groq Whisper, TTS via `gTTS`+`playsound`. Needs `pip install pyaudio gtts playsound`. Contains stale `[cite: N]` fragments (lines ~270-274) — leftover citation markup, ignore.
- `YanAPI.py` — vendored UBTECH REST SDK (`http://<robot_ip>:9090/v1/`). Do not edit or reformat.
- `lib_ukit/` — protobuf transport for `YanAPI`. Do not touch.

## Run
- Always call `YanAPI.yan_api_init(ROBOT_IP)` first; default `ROBOT_IP = "127.0.0.1"` (on-robot). Change only when driving robot remotely.
- On robot: `python3 yanshee_detect_any.py` (Python 3.5-compatible — keep `urllib`, `.format()`, no f-strings/dataclasses).
- Off robot (legacy only): `python3 yanshee_detect.py`; requires mic + `GROQ_API_KEY`.
- No robot available locally: `python3 -m py_compile <file>` is the only safe verification; never call `sync_*` functions without hardware (they block on HTTP + motion completion).

## Conventions / gotchas
- Prefer `sync_*` YanAPI calls (`sync_play_motion`, `sync_do_tts`, `sync_do_face_recognition_value`); they block until completion. `start_*` is fire-and-forget — only used for music (`start_play_music`) with explicit `get_media_music_state()` polling.
- `get_current_gesture()` helper (in `yanshee_detect_any.py`) normalizes the dict-vs-string SDK return; reuse it, and always `.lower()` gesture names (`thumbsup`/`thumbsdown`).
- LED semantics: white-blink = scanning, green-breath = speaking, blue-blink = cloud call, yellow-blink = gesture scan, red-breath = idle.
- Motion names are robot-side `.hts` assets: `reset`, `wave`, `bow`, `crouch`, `turn around`, `joget`; `daftar_lagu` mp3s must already exist on robot. Always `reset` after a dance/motion sequence.
- Secrets are currently hardcoded (`API_KEY` in `yanshee_detect_any.py`, `GROQ_API_KEY` in `yanshee_detect.py`). Do not commit real keys; use placeholders for new code.
