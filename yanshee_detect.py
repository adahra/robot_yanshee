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

# =====================================================================
# CONFIGURATION
# =====================================================================
ROBOT_IP = "127.0.0.1"  # Ganti dengan IP Robot Yanshee Anda
OLLAMA_CLOUD_URL = "https://ollama.com/v1/chat/completions"
API_KEY = "OLLAMA_API_KEY"
MODEL_NAME = "nemotron-3-ultra"

# Masukkan API Key Groq untuk Whisper (Gratis di console.groq.com)
GROQ_API_KEY = "API_KEY_GROQ"  
GROQ_WHISPER_URL = "https://api.groq.com/openai/v1/audio/transcriptions"

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
        with urllib.request.urlopen(req) as response:
            res_body = json.loads(response.read().decode("utf-8"))
            return res_body.get("text", "")
    except Exception as e:
        print("[ASR ERROR]: {}".format(str(e)))
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
    success = YanAPI.sync_play_motion(name=action_name)
    return "Gerakan berhasil." if success else "Gerakan gagal."

def ask_ollama_cloud(user_prompt, gender_context):
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
        with urllib.request.urlopen(req) as response:
            res_body = json.loads(response.read().decode("utf-8"))
            message = res_body['choices'][0]['message']
            
            if message.get("tool_calls"):
                for tool_call in message["tool_calls"]:
                    if tool_call["function"]["name"] == "move_robot":
                        arguments = json.loads(tool_call["function"]["arguments"])
                        action = arguments.get("action")
                        execute_robot_action(action)
                        return "Saya sudah melakukan gerakan {} untuk Anda!".format(action)
                
            return message.get("content", "")
            
    except Exception as e:
        print("[ERROR API]: {}".format(str(e)))
        return "Maaf, terjadi masalah koneksi."

# =====================================================================
# MAIN LOOP
# =====================================================================
def main_loop():
    print("[INIT] Menghubungkan ke robot Yanshee...")
    YanAPI.yan_api_init(ROBOT_IP)
    
    speak_indonesian_gtts("Sistem kecerdasan buatan bahasa Indonesia siap berjalan.")
    
    while True:
        YanAPI.set_robot_led(type="button", color="white", mode="blink")
        print("\n[MEMINDAI] Mencari wajah manusia...")
        
        face_count = YanAPI.sync_do_face_recognition_value(type="quantity")
        
        if face_count and face_count > 0:
            print("[TERDETEKSI] Menemukan {} wajah!".format(face_count))
            
            gender = YanAPI.sync_do_face_recognition_value(type="gender")
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
            
            YanAPI.set_robot_led(type="button", color="green", mode="breath")
            YanAPI.sync_play_motion(name="wave", direction="left")
            YanAPI.sync_play_motion(name="reset")
            
            # Ucapkan Sapaan (TTS gTTS)
            speak_indonesian_gtts(sapaan_terpilih)
            
            # Rekam & Transkrip Audio (ASR Whisper)
            record_audio("user_voice.wav", record_seconds=4)
            user_speech = transcribe_indonesian_whisper("user_voice.wav")
            
            if user_speech and len(user_speech.strip()) > 0:
                print("[WHISPER ASR]: {}".format(user_speech))
                
                YanAPI.set_robot_led(type="button", color="blue", mode="blink")
                
                # Respon dari LLM
                ai_response = ask_ollama_cloud(user_speech, panggilan)
                print("[RESPONSE AI]: {}".format(ai_response))
                
                # Ucapkan Respon (TTS gTTS)
                YanAPI.set_robot_led(type="button", color="green", mode="breath")
                speak_indonesian_gtts(ai_response)
                
            print("[INTERAKSI SELESAI] Jeda pemindaian...")
            time.sleep(3) 
            
        else:
            print("[TIDAK TERDETEKSI] Menjalankan gerakan otomatis...")
            
            YanAPI.sync_do_motion_gait(speed_v=3, steps=3)[cite: 2]
            YanAPI.sync_play_motion(name="bow")[cite: 2]
            YanAPI.sync_play_motion(name="crouch")[cite: 2]
            YanAPI.sync_play_motion(name="GetUp")
            YanAPI.sync_play_motion(name="reset")
        
        time.sleep(1.5)

if __name__ == "__main__":
    main_loop()
