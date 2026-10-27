import json
import time
import random
import urllib.request
import urllib.error
import wave
import pyaudio
import os
from gtts import gTTS
from playsound import playsound
import YanAPI  # Menggunakan file SDK Python dari Anda
import config  # Konfigurasi dan logging


# =====================================================================
# KONFIGURASI
# =====================================================================
_cfg = config.get_config()
log = config.get_logger()

ROBOT_IP = _cfg.get("ROBOT_IP", "127.0.0.1")  # Ganti dengan IP Robot Yanshee Anda
OLLAMA_CLOUD_URL = _cfg.get("OLLAMA_CLOUD_URL", "https://ollama.com/v1/chat/completions")
API_KEY = os.environ.get("OLLAMA_API_KEY", "")
MODEL_NAME = _cfg.get("MODEL_NAME", "nemotron-3-ultra")
REQUEST_TIMEOUT = _cfg.get("REQUEST_TIMEOUT", 30)

# Masukkan API key lewat environment; jangan simpan secret di config.json.
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_WHISPER_URL = "https://api.groq.com/openai/v1/audio/transcriptions"

FALLBACK_MOTION = _cfg.get("FALLBACK_MOTION", "reset")
FALLBACK_TTS = _cfg.get("FALLBACK_TTS", "Maaf, saya tidak dapat terhubung ke layanan cloud. Silakan coba lagi nanti.")


# =====================================================================
# 1. MODUL REKAM AUDIO & ASR (WHISPER API - PYTHON 3.5 COMPATIBLE)
# =====================================================================
def record_audio(filename="temp_input.wav", record_seconds=4):
    """Merekam suara dari mikrofon lokal menggunakan PyAudio"""
    CHUNK = 1024
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 16000

    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)

    print("[ASR] Merekam suara selama {} detik...".format(record_seconds))
    log.info("[ASR] Merekam suara selama {} detik.".format(record_seconds))
    frames = []

    for _ in range(0, int(RATE / CHUNK * record_seconds)):
        data = stream.read(CHUNK)
        frames.append(data)

    print("[ASR] Rekaman selesai.")
    stream.stop_stream()
    stream.close()
    p.terminate()

    wf = wave.open(filename, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(p.getsamplesize(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()

def transcribe_indonesian_whisper(audio_path="temp_input.wav"):
    """Mengirim audio ke Groq Whisper API untuk Speech-to-Text Bahasa Indonesia"""
    if not os.path.exists(audio_path):
        log.warning("[ASR] File audio tidak ditemukan: {}".format(audio_path))
        return ""
    if not GROQ_API_KEY:
        log.warning("[ASR] GROQ_API_KEY belum diset.")
        return ""

    boundary = '---WebKitFormBoundary7MA4YWxkTrZu0gW'
    headers = {
        "Authorization": "Bearer {}".format(GROQ_API_KEY),
        "Content-Type": "multipart/form-data; boundary={}".format(boundary)
    }

    # Manual multipart form-data construction untuk Python 3.5
    body = []

    # Field: model
    body.append('--{}'.format(boundary).encode('utf-8'))
    body.append('Content-Disposition: form-data; name="model"'.encode('utf-8'))
    body.append(b'')
    body.append('whisper-large-v3'.encode('utf-8'))

    # Field: language
    body.append('--{}'.format(boundary).encode('utf-8'))
    body.append('Content-Disposition: form-data; name="language"'.encode('utf-8'))
    body.append(b'')
    body.append('id'.encode('utf-8'))

    # Field: file
    with open(audio_path, 'rb') as f:
        file_content = f.read()

    body.append('--{}'.format(boundary).encode('utf-8'))
    body.append('Content-Disposition: form-data; name="file"; filename="audio.wav"'.encode('utf-8'))
    body.append('Content-Type: audio/wav'.encode('utf-8'))
    body.append(b'')
    body.append(file_content)

    body.append('--{}--'.format(boundary).encode('utf-8'))
    body.append(b'')

    payload = b'\r\n'.join(body)
    req = urllib.request.Request(GROQ_WHISPER_URL, data=payload, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as response:
            res_body = json.loads(response.read().decode("utf-8"))
            return res_body.get("text", "")
    except Exception as e:
        print("[ASR ERROR]: {}".format(str(e)))
        log.error("[ASR ERROR]: {}".format(str(e)))
        return ""

# =====================================================================
# 2. MODUL TTS BAHASA INDONESIA (gTTS - PYTHON 3.5 COMPATIBLE)
# =====================================================================
def speak_indonesian_gtts(text):
    """
    Mengubah teks Bahasa Indonesia ke Audio MP3 via gTTS 2.0.4 dan memutarnya.
    """
    if not text.strip():
        return

    filename = "temp_response.mp3"
    print("[TTS gTTS] Mengucapkan: {}".format(text))
    log.info("[TTS gTTS]: {}".format(text))

    try:
        # Generate file audio MP3 Bahasa Indonesia (lang='id')
        tts = gTTS(text=text, lang='id', slow=False)
        tts.save(filename)

        # Putar file audio
        playsound(filename)

        # Hapus file temporary jika sudah selesai diputar
        if os.path.exists(filename):
            os.remove(filename)
    except Exception as e:
        print("[TTS ERROR]: Gagal memutar gTTS - {}".format(str(e)))
        log.error("[TTS ERROR]: {}".format(str(e)))

# =====================================================================
# TOOL CALLING & AI CONFIG
# =====================================================================
tools = [
    {
        "type": "function",
        "function": {
            "name": "move_robot",
            "description": "Gunakan fungsi ini jika pengguna meminta robot melakukan gerakan fisik.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["wave", "bow", "walk", "raise", "crouch", "reset"],
                        "description": "Jenis gerakan robot."
                    }
                },
                "required": ["action"]
            }
        }
    }
]

def execute_robot_action(action_name):
    print("[FISIK] Menjalankan gerakan: {}".format(action_name))
    log.info("[FISIK] Menjalankan gerakan: {}".format(action_name))
    success = YanAPI.sync_play_motion(name=action_name)
    return "Gerakan berhasil." if success else "Gerakan gagal."

def ask_ollama_cloud(user_prompt, gender_context):
    """Mengirim prompt ke OLLAMA cloud dan mengembalikan (teks, is_fallback).

    Jika cloud tidak tersedia atau API Key belum diatur, mengembalikan
    pesan fallback dan is_fallback=True.
    """
    if not API_KEY or API_KEY == "OLLAMA_API_KEY":
        print("[ERROR] OLLAMA_API_KEY belum dikonfigurasi.")
        log.warning("[ERROR] OLLAMA_API_KEY belum dikonfigurasi.")
        return FALLBACK_TTS, True

    headers = {
        "Authorization": "Bearer {}".format(API_KEY),
        "Content-Type": "application/json"
    }

    system_prompt = "Kamu adalah Yanshee, robot humanoid AI yang ramah. Saat ini kamu sedang berbicara dengan seorang {} di depanmu. Jawablah pertanyaannya dalam Bahasa Indonesia yang singkat dan sopan.".format(gender_context)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "tools": tools,
        "tool_choice": "auto"
    }

    data_bytes = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(OLLAMA_CLOUD_URL, data=data_bytes, headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as response:
            res_body = json.loads(response.read().decode("utf-8"))
            choices = res_body.get("choices") or []
            if not choices:
                print("[ERROR] Respons API tanpa choices: {}".format(res_body))
                log.error("[ERROR] Respons API tanpa choices: {}".format(res_body))
                return FALLBACK_TTS, True
            message = choices[0].get("message") or {}

            if message.get("tool_calls"):
                for tool_call in message["tool_calls"]:
                    if tool_call["function"]["name"] == "move_robot":
                        arguments = json.loads(tool_call["function"]["arguments"])
                        action = arguments.get("action")
                        execute_robot_action(action)
                        return "Saya sudah melakukan gerakan {} untuk Anda!".format(action), False

            return message.get("content", ""), False

    except Exception as e:
        print("[ERROR API]: {}".format(str(e)))
        log.error("[ERROR API]: {}".format(str(e)))
        return FALLBACK_TTS, True

# =====================================================================
# MAIN LOOP
# =====================================================================
def main_loop():
    print("[INIT] Menghubungkan ke robot Yanshee...")
    log.info("[INIT] Menghubungkan ke robot Yanshee di {}".format(ROBOT_IP))
    try:
        YanAPI.yan_api_init(ROBOT_IP)
    except Exception as e:
        log.error("[ERROR] Gagal inisialisasi YanAPI: {}".format(str(e)))
        print("[ERROR] Gagal inisialisasi YanAPI: {}".format(str(e)))
        return

    try:
        speak_indonesian_gtts("Sistem kecerdasan buatan bahasa Indonesia siap berjalan.")
    except Exception as e:
        log.error("[ERROR] Gagal TTS inisialisasi: {}".format(str(e)))

    while True:
        try:
            YanAPI.set_robot_led(type="button", color="white", mode="blink")
        except Exception as e:
            log.error("[ERROR] Gagal set LED: {}".format(str(e)))
        print("\n[MEMINDAI] Mencari wajah manusia...")
        log.info("[MEMINDAI] Mencari wajah manusia...")

        try:
            face_count = YanAPI.sync_do_face_recognition_value(type="quantity")
        except Exception as e:
            log.error("[ERROR] Gagal deteksi wajah: {}".format(str(e)))
            face_count = 0

        if face_count and face_count > 0:
            print("[TERDETEKSI] Menemukan {} wajah!".format(face_count))
            log.info("[TERDETEKSI] {} wajah terdeteksi.".format(face_count))

            try:
                gender = YanAPI.sync_do_face_recognition_value(type="gender")
            except Exception as e:
                log.error("[ERROR] Gagal deteksi gender: {}".format(str(e)))
                gender = ""
            panggilan = "Kakak"
            if gender == "male":
                panggilan = "Tuan"
            elif gender == "female":
                panggilan = "Nyonya"

            sapaan_list = [
                "Halo {}! Senang bertemu dengan Anda.".format(panggilan),
                "Hai {}! Ada yang bisa saya bantu hari ini?".format(panggilan)
            ]
            sapaan_terpilih = random.choice(sapaan_list)

            try:
                YanAPI.set_robot_led(type="button", color="green", mode="breath")
                YanAPI.sync_play_motion(name="wave", direction="left")
                YanAPI.sync_play_motion(name="reset")
            except Exception as e:
                log.error("[ERROR] Gagal gerakan sapaan: {}".format(str(e)))

            # Ucapkan Sapaan (TTS gTTS)
            try:
                speak_indonesian_gtts(sapaan_terpilih)
            except Exception as e:
                log.error("[ERROR] Gagal TTS sapaan: {}".format(str(e)))

            # Rekam & Transkrip Audio (ASR Whisper)
            try:
                record_audio("user_voice.wav", record_seconds=4)
                user_speech = transcribe_indonesian_whisper("user_voice.wav")
            except Exception as e:
                log.error("[ERROR] Gagal rekaman/ASR: {}".format(str(e)))
                user_speech = ""

            if user_speech and len(user_speech.strip()) > 0:
                print("[WHISPER ASR]: {}".format(user_speech))
                log.info("[WHISPER ASR]: {}".format(user_speech))

                try:
                    YanAPI.set_robot_led(type="button", color="blue", mode="blink")
                except Exception:
                    pass

                # Respon dari LLM (dengan fallback)
                try:
                    ai_response, is_fallback = ask_ollama_cloud(user_speech, panggilan)
                except Exception as e:
                    log.error("[ERROR] Gagal memanggil cloud: {}".format(str(e)))
                    ai_response, is_fallback = FALLBACK_TTS, True
                print("[RESPONSE AI]: {}".format(ai_response))
                log.info("[RESPONSE AI] fallback={}: {}".format(is_fallback, ai_response))

                # Ucapkan Respon (TTS gTTS)
                try:
                    YanAPI.set_robot_led(type="button", color="green", mode="breath")
                    speak_indonesian_gtts(ai_response)
                except Exception as e:
                    log.error("[ERROR] Gagal TTS respons: {}".format(str(e)))

                # Mode fallback: cloud tidak tersedia, jalankan gerakan cadangan
                if is_fallback:
                    print("[FALLBACK] Cloud tidak tersedia, menjalankan gerakan cadangan: {}".format(FALLBACK_MOTION))
                    log.warning("[FALLBACK] Cloud tidak tersedia, gerakan cadangan: {}".format(FALLBACK_MOTION))
                    try:
                        YanAPI.sync_play_motion(name=FALLBACK_MOTION)
                    except Exception as e:
                        log.error("[ERROR] Gagal gerakan fallback: {}".format(str(e)))

            print("[INTERAKSI SELESAI] Jeda pemindaian...")
            log.info("[INTERAKSI SELESAI] Jeda pemindaian.")
            time.sleep(3)

        else:
            print("[TIDAK TERDETEKSI] Menjalankan gerakan otomatis...")
            log.info("[TIDAK TERDETEKSI] Tidak ada wajah, jalankan gerakan otomatis.")

            try:
                YanAPI.sync_do_motion_gait(speed_v=3, steps=3)
                YanAPI.sync_play_motion(name="bow")
                YanAPI.sync_play_motion(name="crouch")
                YanAPI.sync_play_motion(name="GetUp")
                YanAPI.sync_play_motion(name="reset")
            except Exception as e:
                log.error("[ERROR] Gagal gerakan otomatis: {}".format(str(e)))

        time.sleep(1.5)

if __name__ == "__main__":
    main_loop()
