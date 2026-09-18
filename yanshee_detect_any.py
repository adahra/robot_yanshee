import json
import time
import random
import urllib.request
import urllib.error
import YanAPI  # Menggunakan file SDK Python

# =====================================================================
# CONFIGURATION
# =====================================================================
ROBOT_IP = "127.0.0.1"
OLLAMA_CLOUD_URL = "https://ollama.com/v1/chat/completions"
API_KEY = "e6b3974837f9431aac72d48de5365545.KE3UcFrOk8NA0yPLm5rUqwNu"
MODEL_NAME = "nemotron-3-ultra"

daftar_lagu = [
    'rollerblade.mp3',
    'ghost.mp3',
    'bojo_galak.mp3',
    'kelingan_mantan.mp3',
    'house.mp3',
    'fukai_mori.mp3',
    'seventeen.mp3',
    'fortune.mp3',
    'cincin.mp3',
    'drop_dead.mp3',
    'uare.mp3',
    'lenka.mp3',
    'sunflower.mp3',
    'hindia.mp3',
    'wind.mp3'
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
    headers = {
        "Authorization": "Bearer {}".format(API_KEY),
        "Content-Type": "application/json"
    }

    system_prompt = "Kamu adalah Yanshee, robot humanoid AI yang ramah. Saat ini kamu sedang berbicara dengan seorang {} di depanmu. Jawablah pertanyaannya dengan sopan.".format(
        gender_context)

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
    req = urllib.request.Request(
        OLLAMA_CLOUD_URL, data=data_bytes, headers=headers)

    try:
        with urllib.request.urlopen(req) as response:
            res_body = json.loads(response.read().decode("utf-8"))
            message = res_body['choices'][0]['message']

            if message.get("tool_calls"):
                for tool_call in message["tool_calls"]:
                    if tool_call["function"]["name"] == "move_robot":
                        arguments = json.loads(
                            tool_call["function"]["arguments"])
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


def play_music_and_loop_motion_sync(music_name, motion_name):
    print("[INFO] Memutar musik: {}".format(music_name))
    res_music = YanAPI.start_play_music(name=music_name)

    if res_music.get("code") != 0:
        print("[ERROR] Gagal memutar musik: {}".format(res_music.get("msg")))
        return

    while True:
        # Cek status musik sebelum memulai gerakan siklus berikutnya
        music_state = YanAPI.get_media_music_state()
        data = music_state.get("data", {})

        status = data.get("status", "")
        current_song = data.get("name", "")

        if status != "run" or current_song != music_name:
            print("[STATUS] Musik berhenti! Menghentikan rutinitas menari...")
            break

        print("[INFO] Menjalankan tarian (sync): {}".format(motion_name))
        # Program tertahan di sini sampai 1 siklus gerakan selesai
        YanAPI.sync_play_motion(name=motion_name)

    YanAPI.sync_play_motion(name="reset")


def play_music_and_loop_motion_fast_stop(music_name, motion_name):
    print("[INFO] Memutar musik: {}".format(music_name))
    res_music = YanAPI.start_play_music(name=music_name)

    if res_music.get("code") != 0:
        print("[ERROR] Gagal memutar musik: {}".format(res_music.get("msg")))
        return

    # time.sleep(0.5)

    # print("[INFO] Mencoba mulai menari: {}".format(motion_name))
    # YanAPI.start_play_motion(name=motion_name)

    while True:
        # Cek gestur ThumbsDown di awal siklus mode interaktif
        if interactive:
            current_gesture = get_current_gesture()  # Gunakan helper
            # Pakai .lower()[cite: 5]
            if current_gesture.lower() == "thumbsdown":
                print(
                    "[STOP] Gestur ThumbsDown terdeteksi. Menghentikan mode interaktif...")
                YanAPI.sync_do_tts(tts="Mode interaktif dihentikan.")
                YanAPI.stop_play_music()
                YanAPI.sync_play_motion(name="reset")
                break

        music_state = YanAPI.get_media_music_state()
        data = music_state.get("data", {})

        status = data.get("status", "")
        current_song = data.get("name", "")

        if status != "run" or current_song != music_name:
            print("[STATUS] Musik berhenti! Menghentikan gerakan robot...")
            YanAPI.stop_play_motion()
            break

        print("[INFO] Mencoba mulai menari: {}".format(motion_name))
        YanAPI.sync_play_motion(name=motion_name)

        # Jeda ditingkatkan ke 1.5 - 2.0 detik agar 1 siklus gerakan joget sempat berjalan
        # time.sleep(1.5)

    YanAPI.sync_play_motion(name="reset")


# =====================================================================
# LOOP UTAMA INTERAKSI
# =====================================================================
def main_loop():
    print("[INIT] Menghubungkan ke robot Yanshee...")
    YanAPI.yan_api_init(ROBOT_IP)
    YanAPI.sync_do_tts(
        tts="Sistem deteksi setiap wajah dan kecerdasan buatan siap berjalan.")
    random_dance(interactive=False)


def main_loop_interactive():
    random_dance(interactive=True)


def random_dance(interactive=False):
    no_speech_count = 0

    while True:
        # Cek gestur ThumbsDown di awal siklus mode interaktif
        if interactive:
            current_gesture = get_current_gesture()  # Gunakan helper
            # Pakai .lower()[cite: 5]
            if current_gesture.lower() == "thumbsdown":
                print(
                    "[STOP] Gestur ThumbsDown terdeteksi. Menghentikan mode interaktif...")
                YanAPI.sync_do_tts(tts="Mode interaktif dihentikan.")
                YanAPI.sync_play_motion(name="reset")
                YanAPI.stop_play_music()

                break

        YanAPI.set_robot_led(type="button", color="white", mode="blink")
        print("\n[MEMINDAI] Mencari wajah manusia di depan kamera...")

        face_count = YanAPI.sync_do_face_recognition_value(type="quantity")

        if face_count and face_count > 0:
            print("[TERDETEKSI] Menemukan {} wajah manusia!".format(face_count))

            gender = YanAPI.sync_do_face_recognition_value(type="gender")

            panggilan = "Kakak"
            if gender == "male":
                panggilan = "Tuan"
            elif gender == "female":
                panggilan = "Nyonya"

            sapaan_list = [
                "Halo {}! Senang melihat Anda di sini.".format(panggilan),
                "Hai {}! Saya robot Yanshee AI, ada yang bisa saya bantu?".format(
                    panggilan),
                "Selamat hari ini {}! Apa yang ingin kita diskusikan kali ini?".format(
                    panggilan)
            ]
            sapaan_terpilih = random.choice(sapaan_list)

            YanAPI.set_robot_led(type="button", color="green", mode="breath")
            YanAPI.sync_play_motion(name="wave", direction="left")
            YanAPI.sync_play_motion(name="reset")
            YanAPI.sync_do_tts(tts=sapaan_terpilih)

            print(
                "[MENDENGAR] Mikrofon aktif, mendengarkan suara {}...".format(panggilan))
            user_speech = YanAPI.sync_do_voice_iat_value()

            if user_speech and len(user_speech.strip()) > 0:
                no_speech_count = 0
                print("[SUARA PENGGUNA]: {}".format(user_speech))

                YanAPI.set_robot_led(type="button", color="blue", mode="blink")

                ai_response = ask_ollama_cloud(user_speech, panggilan)
                print("[RESPONSE AI]: {}".format(ai_response))

                YanAPI.set_robot_led(
                    type="button", color="green", mode="breath")
                YanAPI.sync_do_tts(tts=ai_response)

            else:
                no_speech_count += 1
                print(
                    "[INFO] Tidak ada suara terdeteksi. Hitungan tanpa suara: {}/3".format(no_speech_count))

                if no_speech_count >= 3:
                    print("[AKSI] 3x tidak bersuara! Robot berjalan ke depan...")
                    YanAPI.sync_do_tts(
                        tts="Tidak ada suara. Saya akan berjalan.")
                    # YanAPI.sync_play_motion(name="walk", direction="forward", speed="normal", repeat=3)
                    YanAPI.sync_play_motion(
                        name="turn around", direction="left", repeat=3)
                    YanAPI.sync_play_motion(name="reset")
                    no_speech_count = 0

            print("[INTERAKSI SELESAI] Memberikan jeda sebelum memindai ulang...")
            time.sleep(5)

        else:
            print(
                "[TIDAK TERDETEKSI] Wajah tidak ditemukan. Menjalankan rutinitas alternatif...")
            no_speech_count = 0

            print("-> Belok/Putar kanan 3x")
            YanAPI.sync_play_motion(
                name="turn around", direction="right", repeat=3)

            print("-> Membungkuk (bow)")
            YanAPI.sync_play_motion(name="bow")

            print("-> Jongkok (crouch)")
            YanAPI.sync_play_motion(name="crouch")

            lagu_terpilih = random.choice(daftar_lagu)
            print("-> Memutar lagu acak & joget:", lagu_terpilih)

            play_music_and_loop_motion_fast_stop(lagu_terpilih, "joget")
            # play_music_and_loop_motion_sync(lagu_terpilih, "joget")

            print("-> Reset posisi")
            YanAPI.sync_play_motion(name="reset")

        time.sleep(1.5)


def get_current_gesture():
    """
    Helper untuk mengekstrak nama gestur dari struktur return JSON YanAPI
    """
    res = YanAPI.sync_do_gesture_recognition()

    # Jika return berupa dictionary dan ber-code 0 (normal)
    if isinstance(res, dict) and res.get("code") == 0:
        gesture_name = res.get("data", {}).get("gesture", "")
        return gesture_name

    # Jika SDK YanAPI sudah mem-parse dan langsung mengembalikan string
    elif isinstance(res, str):
        return res

    return ""


# =====================================================================
# GESTURE CONTROLLER (ENTRY POINT)
# =====================================================================
def gesture_control_loop():
    print("[INIT] Menghubungkan ke robot Yanshee...")
    YanAPI.yan_api_init(ROBOT_IP)

    YanAPI.sync_do_tts(
        tts="Sistem pengenal gestur tangan siap. Tunjukkan jempol ke atas untuk memulai.")

    while True:
        YanAPI.set_robot_led(type="button", color="yellow", mode="blink")
        print("\n[GESTURE SCAN] Memindai gestur tangan via kamera...")

        gesture = get_current_gesture()

        if gesture:
            print("[GESTURE CONTROL TERDETEKSI]: {}".format(gesture))
            # Normalisasi ke huruf kecil[cite: 5]
            gesture_lower = gesture.lower()

            if gesture_lower == "thumbsup":
                print("[AKSI] Gestur ThumbsUp terdeteksi! Memulai interaksi AI...")
                YanAPI.set_robot_led(
                    type="button", color="green", mode="breath")
                YanAPI.sync_do_tts(
                    tts="Gestur jempol atas terdeteksi. Memulai mode interaktif.")
                main_loop_interactive()

            elif gesture_lower == "thumbsdown":
                print("[AKSI] Gestur ThumbsDown terdeteksi! Robot dalam posisi Idle.")
                YanAPI.set_robot_led(type="button", color="red", mode="breath")
                YanAPI.sync_do_tts(tts="Robot kembali ke posisi idle.")
                YanAPI.sync_play_motion(name="reset")
                YanAPI.stop_play_music()
                time.sleep(2)

            time.sleep(1)


if __name__ == "__main__":
    gesture_control_loop()
