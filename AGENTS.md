# AGENTS.md — robot_yanshee

Onboard UBTECH Yanshee scripts (run on the robot's Raspberry Pi, Debian). No build, tests, lint, or CI.

## Entry points
- `yanshee_detect_any.py` — current/main. Gesture gate: `gesture_control_loop()` (`thumbsup` → `main_loop_interactive()` → `random_dance(interactive=True)`; `thumbsdown` → idle). Uses onboard mic/TTS via `YanAPI.sync_do_voice_iat_value()` / `sync_do_tts()`. Stdlib only (`json`, `urllib`, `time`, `random`) + `YanAPI`.
- `yanshee_detect.py` — legacy/off-robot variant. Local mic via `pyaudio`, STT via Groq Whisper, TTS via `gTTS`+`playsound`. Needs `pip install -r requirements-legacy.txt`. Deprecated; keep behavior changes minimal and documented.
- `config.py` / `config.json` — runtime config, validation, logging (`load_config`, `get_config`, `get_logger`). `config.json` overrides defaults; invalid values fall back to `DEFAULT_CONFIG`.
- `YanAPI.py` — vendored UBTECH REST SDK (`http://<robot_ip>:9090/v1/`). Do not edit or reformat. It imports `requests`, `nest_asyncio`, `cv2`, `lib_ukit` (protobuf).
- `lib_ukit/` — protobuf transport for `YanAPI`. Do not touch.
- `requirements.txt` / `requirements-legacy.txt` — SDK deps and legacy-only extras.

## Run
- Always call `YanAPI.yan_api_init(ROBOT_IP)` first; default `ROBOT_IP = "127.0.0.1"` (on-robot). Change only when driving robot remotely.
- On robot: `export OLLAMA_API_KEY="..."` then `python3 yanshee_detect_any.py` (Python 3.5-compatible — keep `urllib`, `.format()`, no f-strings/dataclasses).
- Off robot (legacy only): `export GROQ_API_KEY="..."`; requires mic + `pyaudio`/`gtts`/`playsound`.
- No robot available locally: `python3 -m py_compile <file>` is the only safe verification; never call `sync_*` functions without hardware (they block on HTTP + task completion, and have no internal timeout).

## Conventions / gotchas
- Prefer `sync_*` YanAPI calls (`sync_play_motion`, `sync_do_tts`, `sync_do_face_recognition_value`); they block until completion. `start_*` is fire-and-forget — only used for music (`start_play_music`) with explicit `get_media_music_state()` polling.
- `sync_do_face_recognition_value()` returns the value directly (`int` for quantity, `str` for gender/expression, `None` on failure). Existing code also tolerates the dict-wrapped form defensively.
- `get_current_gesture()` normalizes the dict-vs-string SDK return; always `.lower()` gesture names. SDK docs list `ok|good|bad|victory|heart_hand_sign|digital_6_gesture|none`, while the scripts compare `thumbsup`/`thumbsdown` — verify on the robot and note the firmware difference if the gate never fires.
- `move_robot` tool schema accepts `action` (required), `direction` (left/right/both/forward/backward), and `repeat` (1–100). Validation lives in `_normalize_direction()` / `_normalize_repeat()`; per-action directions in `ACTION_DIRECTIONS`, defaults in `DEFAULT_DIRECTIONS`. Executors return `(teks_respons, is_fallback)`.
- `execute_robot_action()` passes `direction=""` for motions that do not take a direction. Do not pass arbitrary direction strings to `sync_play_motion`; the validation helpers exist for this.
- LED semantics: white-blink = scanning, green-breath = speaking, blue-blink = cloud call, yellow-blink = gesture scan, red-breath = idle/low battery.
- Motion names are robot-side `.hts` assets: stock `raise`, `crouch`, `stretch`, `come on`, `wave`, `bend`, `walk`, `turn around`, `head`, `bow`; custom `reset`/`joget` (and legacy `GetUp`). `daftar_lagu` mp3s must already exist at `/home/pi/Documents/music`. Reset after dance/standby sequences.
- Secrets come from environment variables (`OLLAMA_API_KEY`, `GROQ_API_KEY`); never hardcode or commit real keys. Placeholders only in new code.
- Runtime log is `yanshee.log` (gitignored), created by `config.setup_logging()` at import time.
- Update README/AGENTS whenever behavior or config keys change; both are read by agents.
