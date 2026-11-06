# Desain: Dynamic Tool Creation untuk Rutinitas Gerakan Robot Yanshee

## 1. Latar Belakang & Tujuan
LLM membutuhkan kemampuan membuat tool baru secara mandiri saat pengguna meminta aksi komposit atau rutinitas gerakan yang belum ada dalam daftar tool bawaan (`move_robot`). Rutinitas ini didefinisikan sebagai urutan langkah gerakan fisik, dieksekusi secara berurutan, dan disimpan secara persisten dalam berkas JSON agar tetap aktif setelah robot restart.

## 2. Ruang Lingkup
- **Goals**:
  - Menyediakan meta-tool `create_motion_routine` yang dapat dipanggil oleh LLM via function calling.
  - Parameter: `name` (string snake_case), `description` (deskripsi fungsi untuk LLM), `steps` (daftar objek langkah gerakan: `action`, `direction`, `repeat`, `delay`).
  - Validasi setiap langkah: `action` harus anggota `VALID_ACTIONS`, `direction` divalidasi via `_normalize_direction`, `repeat` dibatasi 1–100.
  - Penyimpanan persisten ke `custom_tools.json`.
  - Pemuatan otomatis saat startup skrip (`yanshee_detect_any.py`): mendaftarkan setiap rutinitas ke skema `tools` dan map `tool_executors`.
  - Kompatibel dengan Python 3.5 (tanpa f-string, gunakan `urllib`/`json`/`.format()`).
- **Non-Goals**:
  - Menjalankan kode Python sembarang dari LLM (keamanan hardware robot).
  - Mengubah berkas tarian biner `.hts`.

## 3. Pendekatan yang Dipilih
**Pendekatan 1: Dedicated Meta-Tool + `custom_tools.json`**
- Berkas data terpisah: `custom_tools.json` (format array atau dictionary berisi nama tool, deskripsi, skema parameter, dan langkah-langkah).
- Runner generik: `_create_routine_executor(routine_def)` yang memutar tiap step dengan `execute_robot_action()` dan jeda `time.sleep(delay)`.
- Fallback & safety: Jika eksekusi gagal di tengah urutan, robot melakukan `reset` posisi.

## 4. Struktur Data `custom_tools.json`
```json
{
  "senam_pagi": {
    "name": "senam_pagi",
    "description": "Melakukan rutinitas senam pagi dengan melambai, jongkok, dan peregangan.",
    "steps": [
      {"action": "wave", "direction": "both", "repeat": 2, "delay": 0.5},
      {"action": "crouch", "direction": "", "repeat": 1, "delay": 1.0},
      {"action": "reset", "direction": "", "repeat": 1, "delay": 0.5}
    ]
  }
}
```

## 5. Rencana Pengujian & Verifikasi
- Uji sintaks: `python3 -m py_compile yanshee_detect_any.py`.
- Uji unit/fungsional mandiri via skrip helper Python untuk:
  1. Validasi skema argumen `create_motion_routine`.
  2. Serialisasi dan deserialisasi `custom_tools.json`.
  3. Pendaftaran ke `tools` dan `tool_executors`.
