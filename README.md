# Yanshee AI Face & Voice Interactive System

Sistem interaksi otonom untuk robot humanoid **UBTECH Yanshee** yang menggabungkan deteksi wajah lokal, *Voice-to-Text* (IAT) bawaan robot, dan integrasi **OLLAMA Cloud API** dengan fitur *Function Calling* (Tool Use) untuk eksekusi gerakan fisik secara responsif. Interaksi dibuka dengan gestur jempol ke atas dan dihentikan dengan jempol ke bawah.

---

## 🤖 Tentangnya: Robot Yanshee & Ekosistem Hardware

**UBTECH Yanshee** adalah robot humanoid edukasional berbasis platform terbuka (*open-source*) yang dirancang khusus untuk pembelajaran AI, robotika, dan sistem tertanam (*embedded systems*).

### **Spesifikasi & Arsitektur Hardware:**
- **Main Controller (Brain)**: **Raspberry Pi** (menjalankan OS Linux Debian), bertugas menangani pemrosesan tingkat tinggi seperti Computer Vision, Speech Recognition, konektivitas jaringan, dan eksekusi skrip Python (`YanAPI`).
- **Sub-Controller (Motion/Actuator)**: Microcontroller **STM32F Series**, bertugas mengontrol pergerakan presisi 17 servo digital (sendi), manajemen daya, dan sensor tingkat rendah (*low-level motion control*) secara *real-time*.
- **Hubungan dengan uKit Explore**: Yanshee dan ekosistem **uKit Explore** dari UBTECH berbagi arsitektur servo, protokol komunikasi bus, serta mesin gerakan (*motion engine*) `.hts` yang serupa. Hal ini memudahkan portabilitas file tarian/gerakan antar-platform UBTECH.
- **Integrasi ROS (Robot Operating System)**: Yanshee mendukung integrasi dengan **ROS** (Robot Operating System). Komunikasi antara Raspberry Pi (ROS Master/Node) dan STM32F memungkinkan kontrol kinematika robot yang lebih kompleks, navigasi, serta pemrosesan *sensor fusion* tingkat lanjut.

---

## ✨ Fitur Utama

- **Gerbang Gestur (Gesture Gate)**: Mode siaga memindai gestur tangan. Jempol ke atas (`thumbsup`) memulai sesi interaktif; jempol ke bawah (`thumbsdown`) mengembalikan robot ke posisi idle.
- **Deteksi Wajah & Panggilan Personal**: Menghitung jumlah wajah dan menganalisis gender secara anonim via kamera bawaan untuk menentukan kata sapaan yang sesuai (*Tuan*, *Nyonya*, atau *Kakak*). Ekspresi wajah ikut dipakai untuk memilih sapaan dan konteks *mood* pada prompt LLM.
- **Integrasi LLM Cloud (OLLAMA API)**: Pemrosesan percakapan menggunakan model Cloud AI dengan respons natural berbasis *prompting* kontekstual.
- **Function Calling / Tool Use**: Model AI dapat memutuskan sendiri untuk mengeksekusi gerakan fisik robot (`wave`, `bow`, `walk`, `raise`, `crouch`, `reset`, `turn around`, `joget`), termasuk **arah** (`direction`) dan **jumlah pengulangan** (`repeat` 1–100) bila pengguna menyebutkannya.
- **Mode Fallback**: Bila `OLLAMA_API_KEY` kosong, cloud error, atau respons tidak valid, robot mengucapkan pesan cadangan dan menjalankan gerakan `reset`.
- **Penanganan Kesenyapan (Silence Handling / 3-Strike Rule)**:
  - Pelacakan jumlah interaksi tanpa masukan suara (*3-Strike Counter*).
  - Jika pengguna tidak bersuara sebanyak **3 kali berturut-turut**, robot memberikan umpan balik suara lalu melakukan `YanAPI.sync_play_motion(name="turn around", direction="right", repeat=3)` dan `sync_play_motion(name="reset")`.
- **Mode Standby & Indikasi LED Dada**:
  - **Kedip Putih**: Memindai/mencari wajah manusia.
  - **Napas Hijau**: Interaksi aktif / robot menyapa & berbicara.
  - **Kedip Biru**: Mengirim dan memproses konteks ke Cloud API.
  - **Kedip Kuning**: Memindai gestur tangan.
  - **Napas Merah**: Idle / baterai rendah.
- **Konfigurasi & Logging Terpusat**: Nilai runtime dibaca dari `config.json` (dengan validasi di `config.py`), dan aktivitas dicatat ke `yanshee.log` serta konsol.

---

## 🛠️ Prasyarat & Arsitektur Sistem

- **Hardware**: Robot Humanoid UBTECH Yanshee (Raspberry Pi Mainboard + STM32F Motion Controller).
- **Environment**: Python 3.5+ (berjalan langsung di lingkungan Linux Debian Raspberry Pi Yanshee). Kode dijaga kompatibel dengan Python 3.5: `urllib`, `.format()`, tanpa f-string/dataclass.
- **Dependensi Python**:
  - `YanAPI` (RESTful API Wrapper bawaan Yanshee untuk komunikasi IPC ke pengontrol gerakan STM32)
  - `json`, `time`, `random`, `urllib` (Standard Library)
  - `requests`, `nest_asyncio`, `protobuf`, `opencv-python` (dipakai di dalam `YanAPI.py`/`lib_ukit`)
  - `pyaudio`, `gTTS`, `playsound` (hanya untuk varian lama/off-robot `yanshee_detect.py`)

Instalasi dependensi (lihat [requirements.txt](requirements.txt)):

```bash
pip install -r requirements.txt

# Hanya untuk varian lama/off-robot:
pip install -r requirements-legacy.txt
```

> Di image resmi robot, sebagian besar dependensi sudah terpasang. Untuk OpenCV di Raspberry Pi, paket sistem `python3-opencv` lebih disarankan daripada wheel `pip`.

---

## ⚙️ Konfigurasi

Semua nilai runtime berada di [config.json](config.json) dan divalidasi oleh [config.py](config.py). Jika file tidak ada atau rusak, nilai default di `config.py` dipakai.

| Key | Default | Keterangan |
|---|---|---|
| `ROBOT_IP` | `127.0.0.1` | IP robot; `127.0.0.1` saat skrip berjalan di robot |
| `OLLAMA_CLOUD_URL` | `https://ollama.com/v1/chat/completions` | Endpoint chat OLLAMA Cloud |
| `MODEL_NAME` | `nemotron-3-ultra` | Nama model; pastikan tersedia di akun/Cloud Anda |
| `REQUEST_TIMEOUT` | `30` | Timeout HTTP ke cloud (detik) |
| `NO_SPEECH_LIMIT` | `3` | Jumlah hening sebelum aksi 3-strike |
| `SCAN_DELAY` / `POST_INTERACTION_DELAY` / `GESTURE_SCAN_DELAY` | `1.5` / `5` / `1` | Jeda antar siklus (detik) |
| `BATTERY_LOW_THRESHOLD` | `15` | Ambang baterai rendah (%) |
| `VALID_ACTIONS` | 8 gerakan | Daftar gerakan yang boleh dipanggil LLM |
| `daftar_lagu` | 15 mp3 | Lagu acak untuk mode standby (harus ada di robot) |
| `LOG_FILE` / `LOG_LEVEL` | `yanshee.log` / `INFO` | Tujuan dan level logging |
| `FALLBACK_MOTION` / `FALLBACK_TTS` | `reset` / pesan maaf | Perilaku saat cloud gagal |

**Environment variable (jangan disimpan di repo):**

```bash
export OLLAMA_API_KEY="..."   # wajib untuk yanshee_detect_any.py
export GROQ_API_KEY="..."     # hanya untuk yanshee_detect.py (Whisper)
```

---

## 📂 Struktur File

```text
.
├── yanshee_detect_any.py       # Skrip utama: gerbang gestur + interaksi AI
├── yanshee_detect.py           # Varian lama/off-robot (pyaudio, Groq, gTTS)
├── config.py                   # Konfigurasi, validasi, dan logging
├── config.json                 # Nilai runtime (override default)
├── requirements.txt            # Dependensi SDK YanAPI
├── requirements-legacy.txt     # Dependensi tambahan varian lama
├── YanAPI.py                   # SDK pemanggil endpoint RESTful Yanshee
├── lib_ukit/                   # Transport protobuf untuk YanAPI
│   ├── __init__.py
│   ├── data_pb2.py
│   ├── header_pb2.py
│   └── lib_send.py
└── README.md                   # Dokumentasi proyek
```

---

## 🚀 Menjalankan

**Di robot (cara utama):**

```bash
export OLLAMA_API_KEY="..."
python3 yanshee_detect_any.py
```

**Dari komputer lain (remote):** ubah `ROBOT_IP` di `config.json` ke IP robot, lalu jalankan skrip dari mesin yang satu jaringan.

**Varian lama/off-robot:**

```bash
pip install -r requirements-legacy.txt
export GROQ_API_KEY="..."
python3 yanshee_detect.py
```

Varian ini memakai mikrofon lokal, Groq Whisper untuk STT, dan gTTS untuk TTS — tidak memerlukan fitur mic/TTS onboard.

---

## 🔄 Alur Kerja Logika (Workflow)

1. **Inisialisasi Sistem**:
   - Program menghubungkan modul `YanAPI` ke IP robot, lalu memberikan umpan balik suara (TTS) bahwa sistem siap.
   - Pencacah suara kosong (`no_speech_count`) diinisialisasi ke `0`.

2. **Memindai Gestur (Standby Mode)**:
   - LED dada **kuning berkedip**; kamera memindai gestur tangan.
   - `thumbsup` → masuk mode interaktif. `thumbsdown` → idle (TTS, `reset`, stop musik).

3. **Mode Interaktif** (`random_dance(interactive=True)`):
   - LED dada **putih berkedip**, kamera memindai wajah.
   - **Kondisi A: Wajah Terdeteksi (`face_count > 0`)**
     1. Menganalisis gender dan ekspresi; memilih sapaan acak (*Tuan*, *Nyonya*, *Kakak*).
     2. LED **hijau bernapas**, robot melambaikan tangan (`wave`), lalu menyapa via TTS.
     3. Mikrofon IAT aktif mendengarkan masukan suara.
     4. **Jika Ada Suara Pengguna**:
        - Reset `no_speech_count` ke `0`.
        - LED **biru berkedip** saat mengirim prompt ke Cloud API.
        - Jika LLM memanggil `move_robot`, robot mengeksekusi `action` + `direction` + `repeat` yang diminta, lalu mengucapkan konfirmasi via TTS. Jika tidak, jawaban teks LLM yang diucapkan.
     5. **Jika Tidak Ada Suara (Hening)**:
        - Tambah `no_speech_count` (+1).
        - Jika `no_speech_count >= 3`, robot memberi notifikasi suara, melakukan `turn around` kanan 3x, `reset`, dan mereset pencacah.
   - **Kondisi B: Wajah Tidak Terdeteksi**
     1. Reset `no_speech_count` ke `0`.
     2. Rutinitas standby: `turn around` kanan 3x → `bow` → `crouch` → (jika `daftar_lagu` non-kosong) lagu acak + `joget` via `play_music_and_loop_motion_fast_stop()` → `reset`.
   - **Baterai**: dicek tiap 10 iterasi; di bawah ambang robot memberi peringatan dan melewati gerakan.

4. **Jeda & Pengulangan**:
   - Jeda `POST_INTERACTION_DELAY` setelah interaksi dan `SCAN_DELAY` di akhir siklus sebelum memindai ulang.
   - `random_dance()` dibatasi `max_iterations = 200` sebagai *safety valve*, lalu kembali ke pemindaian gestur.

---

## 🧪 Verifikasi Tanpa Robot

Tidak ada test suite/CI. Verifikasi aman tanpa hardware:

```bash
python3 -m py_compile yanshee_detect_any.py yanshee_detect.py config.py
```

Jangan memanggil fungsi `sync_*` tanpa robot — fungsi tersebut memblokir sampai tugas selesai dan tidak memiliki timeout internal.

---

## ❗ Catatan & Troubleshooting

- **Gestur tidak terdeteksi**: docstring SDK menyebut nilai gestur `good`/`bad` (jempol), sedangkan kode membandingkan `thumbsup`/`thumbsdown`. Nilai aktual bergantung firmware; cek baris `[GESTURE CONTROL TERDETEKSI]` di `yanshee.log`. Bila yang muncul `good`/`bad`, perlu normalisasi di `gesture_control_loop()`.
- **Lagu/tarian tidak jalan**: file mp3 harus ada di `/home/pi/Documents/music`, dan aset `.hts` (`joget`, `reset`, dll.) harus tersedia di robot.
- **`ModuleNotFoundError`**: pasang dependensi via `requirements.txt`; untuk `cv2` di robot gunakan `python3-opencv`.
- **Cloud gagal / `401` / model tidak ditemukan**: robot akan memakai `FALLBACK_TTS` + `FALLBACK_MOTION`; periksa `OLLAMA_API_KEY`, `MODEL_NAME`, dan `OLLAMA_CLOUD_URL` di log.
- **Log**: `yanshee.log` dibuat di direktori kerja dan sudah di-.gitignore.
- **Kompatibilitas**: target robot adalah Python 3.5 — jangan menambahkan f-string, `dataclass`, atau sintaks 3.6+.

---

## 🔐 Keamanan

Jangan menyimpan API key di kode atau `config.json`. Gunakan environment variable (`OLLAMA_API_KEY`, `GROQ_API_KEY`) dan pastikan `.env`/log tidak ikut ter-commit.
