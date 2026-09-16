# Yanshee AI Face & Voice Interactive System

Sistem interaksi otonom untuk robot humanoid **UBTECH Yanshee** yang menggabungkan deteksi wajah lokal, *Voice-to-Text* (IAT) bawaan robot, dan integrasi **OLLAMA Cloud API** dengan fitur *Function Calling* (Tool Use) untuk eksekusi gerakan fisik secara responsif.

---

## 🤖 Tentangnya: Robot Yanshee & Ekosistem Hardware

**UBTECH Yanshee** adalah robot humanoid edukasional berbasis platform terbuka (*open-source*) yang dirancang khusus untuk pembelajaran AI, robotika, dan sistem tertanam (*embedded systems*).

### **Spesifikasi & Arsitektur Hardware:**
- **Main Controller (Brain)**: **Raspberry Pi** (menjalankan OS Linux Debian), bertugas menangani pemrosesan tingkat tinggi seperti Computer Vision, Speech Recognition, konektivitas jaringan, dan eksekusi skrip Python (`YanAPI`).
- **Sub-Controller (Motion/Actuator)**: Microcontroller **STM32F Series**, bertugas mengontrol pergerakan presisi 17 servo digital (sendi), manajemen daya, dan sensor tingkat rendah (*low-level motion control*) secara *real-time*.
- **Hubungan dengan uKit Explore**: Yanshee dan ekosistem **uKit Explore** dari UBTECH berbagi arsitektur servo, protokol komunikasi bus, serta mesin gerakan (*motion engine*) `.hts` yang serupa. Hal ini memudahkan portabilitas file tarian/gerakan antar-platform UBTECH.
- **Integrasi ROS (Robot Operating System)**: Yanshee mendukung integrasi dengan **ROS** (Robot Operating System). Komunikasi antara Raspberry Pi (ROS Master/Node) dan STM32F memungkinkan kontrol kinematika robot yang lebih kompleks, navigasi, serta pemrosesan *sensor fusion* tingkat lanjut.

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

- **Hardware**: Robot Humanoid UBTECH Yanshee (Raspberry Pi Mainboard + STM32F Motion Controller).
- **Environment**: Python 3.5+ (Berjalan langsung di lingkungan Linux Debian Raspberry Pi Yanshee).
- **Library Python**:
  - `YanAPI` (RESTful API Wrapper bawaan Yanshee untuk komunikasi IPC ke pengontrol gerakan STM32)
  - `json`, `time`, `random`, `urllib` (Standard Library)

---

## 📂 Struktur File

```text
.
├── yanshee_detect_any.py   # Skrip utama interaksi AI & deteksi wajah
├── YanAPI.py               # SDK pemanggil endpoint RESTful Yanshee
└── README.md               # Dokumentasi proyek
```

---

## 🔄 Alur Kerja Logika (Workflow)

1. **Inisialisasi Sistem**:
   * Program menghubungkan modul `YanAPI` ke IP robot dan memberikan umpan balik suara (TTS) bahwa sistem AI siap.
   * Pencacah suara kosong (`no_speech_count`) diinisialisasi ke angka `0`.

2. **Memindai Ruangan (Standby Mode)**:
   * LED dada robot diatur ke mode **berkedip putih**.
   * Kamera memindai dan menghitung jumlah wajah di depannya.

3. **Percabangan Kondisi**:
   * **Kondisi A: Wajah Terdeteksi (`face_count > 0`)**
     1. Menganalisis gender (pria/wanita/anonim) dan memilih sapaan acak (*Tuan*, *Nyonya*, atau *Kakak*).
     2. LED dada berubah menjadi **hijau bernapas**, robot melambaikan tangan (`wave`), lalu menyapa via TTS.
     3. Mikrofon IAT aktif mendengarkan masukan suara.
     4. **Jika Ada Suara Pengguna**:
        * Reset `no_speech_count` ke `0`.
        * LED dada **berkedip biru** saat mengirim *prompt* ke Cloud API.
        * Respons teks diucapkan via TTS; jika AI memanggil fungsi gerakan (*function calling*), robot mengeksekusi gerakan fisik yang diminta.
     5. **Jika Tidak Ada Suara (Hening)**:
        * Tambah pencacah `no_speech_count` (+1).
        * Jika `no_speech_count >= 3`, robot memberikan notifikasi suara via TTS, berputar kanan 3 langkah (`sync_do_motion_gait(speed_h=3, steps=3)`), dan mereset pencacah ke `0`.
   * **Kondisi B: Wajah Tidak Terdeteksi**
     1. Reset `no_speech_count` ke `0`.
     2. Jalankan rutinitas *standby* bawaan (maju 3 langkah, membungkuk, jongkok, bangkit, dan kembali ke posisi netral).

4. **Jeda Loop**:
   * Memberikan jeda (*delay*) singkat sebelum mengulang siklus pemindaian dari awal.
