import json
import time
import random
import urllib.request
import urllib.error
import YanAPI  # Menggunakan file SDK Python

# =====================================================================
# CONFIGURATION
# =====================================================================
ROBOT_IP = "127.0.0.1"  # Ganti dengan IP Robot Yanshee Anda
OLLAMA_CLOUD_URL = "https://ollama.com/v1/chat/completions" # URL Chat Completions API
API_KEY = "OLLAMA_API_KEY" # Masukkan API Key Anda di sini
MODEL_NAME = "nemotron-3-ultra"  # Ganti dengan model di cloud Anda

daftar_lagu = [
    "bojo_galak.mp3",
    "helikopter.mp3",
    "house.mp3",
    "fukai_mori.mp3",
    "seventeen.mp3",
    "fortune.mp3",
    "lenka.mp3",
    "wind.mp3"
]

# =====================================================================
# DEFINISI GERAKAN FISIK (FUNCTION CALLING)
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
    """
    Mengirim teks ke Cloud API menggunakan urllib.request (Kompatibel Python 3.5)
    """
    headers = {
        "Authorization": "Bearer {}".format(API_KEY),
        "Content-Type": "application/json"
    }
    
    system_prompt = "Kamu adalah Yanshee, robot humanoid AI yang ramah. Saat ini kamu sedang berbicara dengan seorang {} di depanmu. Jawablah pertanyaannya dengan sopan.".format(gender_context)
    
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

    # Encode payload JSON ke bentuk bytes untuk urllib
    data_bytes = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(OLLAMA_CLOUD_URL, data=data_bytes, headers=headers)

    try:
        with urllib.request.urlopen(req) as response:
            res_body = json.loads(response.read().decode("utf-8"))
            message = res_body['choices'][0]['message']
            
            # Memeriksa apakah AI meminta eksekusi fungsi (Tool Calls)
            if message.get("tool_calls"):
                for tool_call in message["tool_calls"]:
                    if tool_call["function"]["name"] == "move_robot":
                        arguments = json.loads(tool_call["function"]["arguments"])
                        action = arguments.get("action")
                        execute_robot_action(action)
                        return "Saya sudah melakukan gerakan {} untuk Anda!".format(action)
                
            return message.get("content", "")
            
    except urllib.error.HTTPError as e:
        error_msg = e.read().decode("utf-8")
        print("[HTTP ERROR]: STATUS {} - {}".format(e.code, error_msg))
        return "Terjadi masalah pada koneksi API."
    except Exception as e:
        print("[ERROR]: {}".format(str(e)))
        return "Koneksi ke cloud terganggu."


# =====================================================================
# LOOP UTAMA (DETEKSI SETIAP WAJAH + SAPA + MENDENGAR PERINTAH)
# =====================================================================
def main_loop():
    print("[INIT] Menghubungkan ke robot Yanshee...")
    YanAPI.yan_api_init(ROBOT_IP)
    
    YanAPI.sync_do_tts(tts="Sistem deteksi setiap wajah dan kecerdasan buatan siap berjalan.")
    
    # Inisialisasi variabel penghitung tidak bersuara
    no_speech_count = 0
    
    while True:
        # Lampu dada berkedip putih menandakan mode standby / memindai ruangan
        YanAPI.set_robot_led(type="button", color="white", mode="blink")
        print("\n[MEMINDAI] Mencari wajah manusia di depan kamera...")
        
        # 1. Cek apakah ada wajah di depan kamera (Mengembalikan angka int jumlah wajah)
        face_count = YanAPI.sync_do_face_recognition_value(type="quantity")
        
        if face_count and face_count > 0:
            print("[TERDETEKSI] Menemukan {} wajah manusia!".format(face_count))
            
            # 2. Analisis gender orang tersebut secara anonim untuk sapaan lebih personal
            gender = YanAPI.sync_do_face_recognition_value(type="gender") # Output: "male", "female", atau "none"
            
            # Menentukan panggilan bahasa Indonesia berdasarkan gender
            panggilan = "Kakak"
            if gender == "male":
                panggilan = "Tuan"
            elif gender == "female":
                panggilan = "Nyonya"
                
            # Variasi kalimat sapaan acak agar robot tidak monoton
            sapaan_list = [
                "Halo {}! Senang melihat Anda di sini.".format(panggilan),
                "Hai {}! Saya robot Yanshee AI, ada yang bisa saya bantu?".format(panggilan),
                "Selamat hari ini {}! Apa yang ingin kita diskusikan kali ini?".format(panggilan)
            ]
            sapaan_terpilih = random.choice(sapaan_list)
            
            # Robot menyapa secara proaktif dan melambaikan tangan
            YanAPI.set_robot_led(type="button", color="green", mode="breath") # LED Hijau tanda interaksi aktif
            YanAPI.sync_play_motion(name="wave", direction="left") # Gerakan melambaikan tangan memberi salam
            YanAPI.sync_play_motion(name="reset")
            YanAPI.sync_do_tts(tts=sapaan_terpilih)
            
            # 3. Buka Mikrofon setelah menyapa untuk mendengar perintah suara
            print("[MENDENGAR] Mikrofon aktif, mendengarkan suara {}...".format(panggilan))
            user_speech = YanAPI.sync_do_voice_iat_value()
            
            if user_speech and len(user_speech.strip()) > 0:
                # Reset counter jika pengguna bersuara
                no_speech_count = 0
                
                print("[SUARA PENGGUNA]: {}".format(user_speech))
                
                # Indikator berkedip biru (Sedang memproses ke Cloud API)
                YanAPI.set_robot_led(type="button", color="blue", mode="blink")
                
                # 4. Kirim ke API Cloud
                ai_response = ask_ollama_cloud(user_speech, panggilan)
                print("[RESPONSE AI]: {}".format(ai_response))
                
                # 5. Ucapkan jawaban AI lewat speaker robot
                YanAPI.set_robot_led(type="button", color="green", mode="breath")
                YanAPI.sync_do_tts(tts=ai_response)
                
            else:
                # Tambah hitungan jika tidak ada suara terdeteksi
                no_speech_count += 1
                print("[INFO] Tidak ada suara terdeteksi. Hitungan tanpa suara: {}/3".format(no_speech_count))
                
                # Jika sudah 3 kali berturut-turut tidak ada suara
                if no_speech_count >= 3:
                    print("[AKSI] 3x tidak bersuara! Robot berbelok ke kanan...")
                    YanAPI.sync_do_tts(tts="Tidak ada suara. Saya akan berbelok ke kanan.")
                    
                    # Gerakan belok kanan menggunakan gait (geser kanan / berputar)
                    #YanAPI.sync_do_motion_gait(speed_v=0, speed_h=3, steps=3)
                    YanAPI.sync_play_motion(name="walk", direction="forward", speed="normal", repeat=3)
                    #YanAPI.exit_motion_gait()
                    YanAPI.sync_play_motion(name="reset")
                    
                    # Reset kembali hitungan ke 0 setelah aksi belok selesai
                    no_speech_count = 0
                
            # Jeda interaksi agar robot tidak menyapa orang yang sama berulang-ulang
            print("[INTERAKSI SELESAI] Memberikan jeda sebelum memindai ulang...")
            time.sleep(5)
            
        else:
            print("[TIDAK TERDETEKSI] Wajah tidak ditemukan. Menjalankan rutinitas alternatif...")
            
            # Reset counter jika tidak ada wajah
            no_speech_count = 0
            
            # 1. Maju 3 langkah
            print("-> Maju 3 langkah")
            YanAPI.sync_do_motion_gait(speed_v=3, steps=3)
            
            # 2. Melakukan gerakan bow (membungkuk/memberi hormat)
            print("-> Membungkok (bow)")
            YanAPI.sync_play_motion(name="bow")
                
            # 3. Melakukan gerakan crouch (jongkok)
            print("-> Jongkok (crouch)")
            YanAPI.sync_play_motion(name="crouch")
            
            print("-> Putar musik secara acak")
            lagu_sekarang = ganti_lagu_acak()
            
            # 4. Bangkit dari posisi jongkok
            #print("-> Bangkit (GetUp)")
            #YanAPI.sync_play_motion(name="pameran")
            print("-> Jalankan motion berdasar musik")
            # play_music_and_loop_motion(lagu_sekarang, "joget")
            play_music_and_loop_motion_fast_stop(lagu_sekarang, "joget")
            
            # 5. Mengembalikan robot ke posisi awal/netral
            print("-> Reset posisi")
            YanAPI.sync_play_motion(name="reset")
        
        # Jeda scan standar saat mode standby
        time.sleep(1.5)
        

def ganti_lagu_acak():
    # Pilih satu lagu secara acak dari list
    lagu_terpilih = random.choice(daftar_lagu)
    print("Mencoba memutar lagu acak:", lagu_terpilih)
    
    # Putar lagu yang terpilih
    res = YanAPI.start_play_music(name=lagu_terpilih)
    
    # Cek respon dari API
    if res.get("code") == 0:
        print("Berhasil memutar:", lagu_terpilih)
    else:
        print("Gagal memutar lagu. Pesan error:", res.get("msg"))
        
    return lagu_terpilih
    
        
def play_music_and_loop_motion_fast_stop(music_name, motion_name):
    # 1. Putar musik (Non-blocking)
    print("[INFO] Memutar musik: {}".format(music_name))
    res_music = YanAPI.start_play_music(name=music_name)
    
    if res_music.get("code") != 0:
        print("[ERROR] Gagal memutar musik:", res_music.get("msg"))
        return

    time.sleep(1.0) # Jeda singkat agar player audio aktif

    while True:
        # Cek status musik
        music_state = YanAPI.get_media_music_state()
        data = music_state.get("data", {})
        
        status = data.get("status", "")
        current_song = data.get("name", "")
        
        # Jika musik sudah mati, SEGERA hentikan gerakan
        if status != "run" or current_song != music_name:
            print("[STATUS] Musik berhenti! Menghentikan gerakan robot...")
            YanAPI.stop_play_motion() # Hentikan gerakan saat itu juga
            break
            
        # Pemicu gerakan versi non-blocking
        # Memulai gerakan tanpa menahan (block) eksekusi program
        YanAPI.sync_play_motion(name=motion_name)
        
        # Lakukan polling dengan jeda kecil agar program bisa terus mengecek status musik
        # Jeda 0.2 detik membuat pengecekan musik sangat responsif
        #for _ in range(10): # 10 x 0.2 detik = 2 detik (estimasi durasi 1 siklus gerakan)
        #    time.sleep(0.2)
            
            # Cek cepat di dalam jeda
        #    st = YanAPI.get_media_music_state().get("data", {}).get("status", "")
        #    if st != "run":
        #        YanAPI.stop_play_motion()
        #        break

    # Netralkan kembali posisi robot
    YanAPI.sync_play_motion(name="reset")
        
        
def jalan_memutar_sync_motion(total_putaran=4):
    YanAPI.sync_play_motion(name="reset")
    
    for i in range(total_putaran):
        print("Siklus ke-{}: Maju dan Belok...".format(i + 1))
        
        # 1. Melangkah maju 3 kali
        YanAPI.sync_play_motion(
            name="walk", 
            direction="forward", 
            speed="normal", 
            repeat=3
        )
        
        YanAPI.sync_play_motion(name="turn around", direction="left", repeat=1)
        
        # 2. Belok/Geser ke kanan 1 kali untuk memberi efek memutar
        YanAPI.sync_play_motion(
            name="walk", 
            direction="right", 
            speed="normal", 
            repeat=1
        )
        
        time.sleep(0.5)

    # Cukup reset posisi (tidak perlu exit_motion_gait)
    YanAPI.sync_play_motion(name="reset")
    
    
if __name__ == "__main__":
    main_loop()
