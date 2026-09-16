# Yanshee AI Face & Voice Interactive System

Sistem interaksi otonom untuk robot humanoid **UBTECH Yanshee** yang menggabungkan deteksi wajah lokal, *Voice-to-Text* (IAT) bawaan robot, dan integrasi **OLLAMA Cloud API** dengan fitur *Function Calling* (Tool Use) untuk eksekusi gerakan fisik secara responsif.

---

## 🔑 Fitur Utama

- **Deteksi Wajah & Panggilan Personal**: Menghitung jumlah wajah dan menganalisis gender secara anonim via kamera bawaan untuk menentukan kata sapaan yang sesuai (*Tuan*, *Nyonya*, atau *Kakak*).
- **Integrasi LLM Cloud (OLLAMA API)**: Pemrosesan percakapan menggunakan model Cloud AI dengan respon alami berbasis *prompting* kontekstual.
- **Function Calling / Tool Use**: Model AI dapat memutuskan secara mandiri untuk mengeksekusi gerakan fisik robot (`wave`, `bow`, `walk`, `crouch`, `reset`) sesuai instruksi pengguna.
- **Penanganan Kesenyapan (Silence Handling / 3-Strike Rule)**:
  - Pelacakan jumlah interaksi tanpa masukan suara (*3-Strike Counter*).
  - Jika pengguna tidak bersuara sebanyak **3 kali berturut-turut**, robot secara otomatis memberikan umpan balik suara dan melakukan gerakan belok kanan (*gait rotation*).
- **Mode Standby & Indikasi LED Dada**:
  - **Kedip Putih**: Memindai/mencari wajah manusia.
  - **Napas Hijau**: Interaksi aktif / robot menyapa & berbicara.
  - **Kedip Biru**: Mengirim dan memproses konteks ke Cloud API.

---

## 🛠️ Prasyarat & Arsitektur Sistem

- **Hardware**: Robot Humanoid UBTECH Yanshee.
- **Environment**: Python 3.5+ (Kompatibel dengan lingkungan bawaan Debian Linux Yanshee).
- **Library Python**:
  - `YanAPI` (RESTful API Wrapper bawaan Yanshee)
  - `json`, `time`, `random`, `urllib` (Standard Library)

---

## 📂 Struktur File

```text
.
├── yanshee_detect_any.py   # Skrip utama interaksi AI & deteksi wajah
├── YanAPI.py               # SDK pemanggil endpoint RESTful Yanshee
└── README.md               # Dokumentasi proyek
