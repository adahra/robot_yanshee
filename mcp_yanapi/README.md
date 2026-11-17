# YanAPI MCP Server

MCP server yang meng-export YanAPI functions sebagai tools melalui FastMCP JSON-RPC.

## Cara Kerja

- **Server**: Menggunakan FastMCP dari MCP SDK (v1)
- **Protocol**: JSON-RPC melalui stdin/stdout (MCP standard)
- **Init**: Menjalankan `yan_api_init()` dengan robot IP (default 127.0.0.1)

## Instalasi

```bash
pip install -r requirements.txt
```

## Jalankan Server

```bash
python3 mcp_yanapi_server.py [--robot-ip 192.168.1.XX] [--log-level INFO|DEBUG]
```

## Tools

Server meng-export function-tool berikut (nama = YanAPI function name yang canonical):

### Motion
- `sync_play_motion` – execute motion + wait
- `start_play_motion` – start motion (non-blocking)

### Music
- `sync_play_music` – play music + wait
- `start_play_music` – start music (non-blocking)
- `stop_play_music` – stop music

### TTS / Voice
- `sync_do_tts` – text-to-speech
- `sync_do_voice_iat_value` – voice-to-text

### LED
- `sync_set_led` – set LED type, color, mode

### Gait
- `sync_do_motion_gait` – execute gait

### Vision
- `sync_do_face_recognition_value` – recognize faces
- `sync_do_QR_code_recognition` – QR code recognition

### Sensor & State
- `get_robot_battery_value` – baterai persentase
- `get_robot_volume_value` – volume
- `get_motion_list_value` – daftar motion
- `get_media_music_list` – daftar musik

### Servos
- `sync_set_servo_rotate` – set servo angles

## Contoh CLI

```bash
# Muat server sebagai MCP tool di OpenCode
mcp://yanapi

# Menggunakan mcp-client yang compatible
nanobot mcp://yanapi sync_play_motion name="wave" speed="normal" repeat=2
```

## Files Terkait

- `mcp_yanapi_server.py` – implementasi
- `requirements.txt` – dependensi
- `YanAPI.py` – SDK robot yang diimpor

## Catatan

- Ensure the robot IP address (`--robot-ip`) sesuai dengan IP robot di jaringan yang sama.
- Server hanya blocking functions dalam thread pool (FastMCP default async).
- Semua response dikembalikan sebagai JSON; error di-expose sebagai field `error`.
- MCPServer bisa dijalankan bersamaan (multiple instances) dengan IP yang berbeda.
- Ini sesuai dengan semua YanAPI functions yang ada; fungsi yang hilang bisa ditambahkan di `YANAPI_TOOLS`.

## Troubleshooting

- Jika `yan_api_init` gagal (robot tidak merespon), server akan tetap jalan namun tool calls akan error.
- Jika log menunjukkan "Error calling yanapi.sync_play_motion: ...", pastikan robot tersambung ke `http://<ip>:9090/v1`.
- Gunakan `get_robot_battery_value` untuk cek status robot sebelum motion.

## Roadmap

- Tambahkan streaming control untuk `start_*` functions (polling status async)
- Expose semua API `get_*` dan `set_*` functions.
- Tambahkan health check / ping endpoint.
- Tambahkan command-line arguments untuk mock robot mode (skip HTTP calls).