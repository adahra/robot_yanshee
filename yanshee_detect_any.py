import json
import os
import time
import random
import urllib.request
import urllib.error
import YanAPI  # Menggunakan file SDK Python
import config  # Konfigurasi dan logging


# =====================================================================
# KONFIGURASI
# =====================================================================
_cfg = config.get_config()
log = config.get_logger()

ROBOT_IP = _cfg.get("ROBOT_IP", "127.0.0.1")
OLLAMA_CLOUD_URL = _cfg.get("OLLAMA_CLOUD_URL", "https://ollama.com/v1/chat/completions")
API_KEY = os.environ.get("OLLAMA_API_KEY", "")
MODEL_NAME = _cfg.get("MODEL_NAME", "nemotron-3-ultra")
REQUEST_TIMEOUT = _cfg.get("REQUEST_TIMEOUT", 30)

NO_SPEECH_LIMIT = _cfg.get("NO_SPEECH_LIMIT", 3)
SCAN_DELAY = _cfg.get("SCAN_DELAY", 1.5)
POST_INTERACTION_DELAY = _cfg.get("POST_INTERACTION_DELAY", 5)
GESTURE_SCAN_DELAY = _cfg.get("GESTURE_SCAN_DELAY", 1)
BATTERY_LOW_THRESHOLD = _cfg.get("BATTERY_LOW_THRESHOLD", 15)

VALID_ACTIONS = tuple(_cfg.get("VALID_ACTIONS", ["wave", "bow", "walk", "raise",
                                                    "crouch", "reset", "turn around", "joget"]))

daftar_lagu = _cfg.get("daftar_lagu", [])

FALLBACK_MOTION = _cfg.get("FALLBACK_MOTION", "reset")
FALLBACK_TTS = _cfg.get("FALLBACK_TTS", "Maaf, saya tidak dapat terhubung ke layanan cloud. Silakan coba lagi nanti.")

# Label ekspresi wajah (hasil sync_do_face_recognition_value type="expression")
# untuk konteks mood pada prompt LLM. "normal"/"none" = tanpa konteks mood.
EXPRESSION_LABELS = {
    "happy": "sangat senang dan bersemangat",
    "sad": "sedih dan lesu",
    "anger": "marah atau kesal",
    "disgust": "tidak suka atau muak",
    "fear": "takut atau cemas",
    "surprised": "kaget",
    "normal": "netral",
    "none": "",
}


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
                        "enum": list(VALID_ACTIONS),
                        "description": "Jenis gerakan robot."
                    }
                },
                "required": ["action"]
            }
        }
    }
]


def execute_robot_action(action_name):
    if action_name not in VALID_ACTIONS:
        log.warning("[FISIK] Aksi tidak dikenal: {}".format(action_name))
        print("[FISIK] Aksi tidak dikenal: {}".format(action_name))
        return False
    print("[FISIK] Menjalankan gerakan: {}".format(action_name))
    log.info("[FISIK] Menjalankan gerakan: {}".format(action_name))
    try:
        return bool(YanAPI.sync_play_motion(name=action_name))
    except Exception as e:
        log.error("[FISIK] Gerakan gagal: {}".format(str(e)))
        return False


def ask_ollama_cloud(user_prompt, gender_context, expression_context=""):
    """Mengirim prompt ke OLLAMA cloud dan mengembalikan (teks, is_fallback).

    Jika cloud tidak tersedia atau API Key belum diatur, mengembalikan
    pesan fallback dan is_fallback=True agar pemanggil dapat memutar
    gerakan cadangan.
    """
    if not API_KEY:
        log.warning("[ERROR] OLLAMA_API_KEY belum diset.")
        print("[ERROR] OLLAMA_API_KEY belum diset.")
        return FALLBACK_TTS, True

    headers = {
        "Authorization": "Bearer {}".format(API_KEY),
        "Content-Type": "application/json"
    }

    system_prompt = "Kamu adalah Yanshee, robot humanoid AI yang ramah. Saat ini kamu sedang berbicara dengan seorang {} di depanmu".format(
        gender_context)
    if expression_context:
        system_prompt += ". Dari wajahnya, ia tampak {}".format(expression_context)
    system_prompt += ". Jawablah pertanyaannya dengan sopan, dan sesuaikan balasanmu dengan perasaannya."

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
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as response:
            res_body = json.loads(response.read().decode("utf-8"))
            choices = res_body.get("choices") or []
            if not choices:
                log.error("[ERROR] Respons API tanpa choices: {}".format(res_body))
                print("[ERROR] Respons API tanpa choices: {}".format(res_body))
                return FALLBACK_TTS, True
            message = choices[0].get("message") or {}

            if message.get("tool_calls"):
                for tool_call in message["tool_calls"]:
                    func = (tool_call or {}).get("function") or {}
                    if func.get("name") == "move_robot":
                        try:
                            arguments = json.loads(func.get("arguments") or "{}")
                        except ValueError:
                            log.error("[ERROR] Argumen tool_call bukan JSON: {}".format(func.get("arguments")))
                            print("[ERROR] Argumen tool_call bukan JSON: {}".format(func.get("arguments")))
                            continue
                        action = arguments.get("action")
                        success = execute_robot_action(action)
                        if success:
                            return "Saya sudah melakukan gerakan {} untuk Anda!".format(action), False
                        return "Maaf, gerakan {} gagal dilakukan.".format(action), False

            content = message.get("content", "") or ""
            if not content.strip():
                return FALLBACK_TTS, True
            return content, False

    except urllib.error.HTTPError as e:
        error_msg = e.read().decode("utf-8")
        log.error("[HTTP ERROR]: STATUS {} - {}".format(e.code, error_msg))
        print("[HTTP ERROR]: STATUS {} - {}".format(e.code, error_msg))
        return FALLBACK_TTS, True
    except Exception as e:
        log.error("[ERROR]: {}".format(str(e)))
        print("[ERROR]: {}".format(str(e)))
        return FALLBACK_TTS, True


def play_music_and_loop_motion_fast_stop(music_name, motion_name, interactive=False):
    print("[INFO] Memutar musik: {}".format(music_name))
    log.info("[INFO] Memutar musik: {}".format(music_name))
    try:
        res_music = YanAPI.start_play_music(name=music_name) or {}
    except Exception as e:
        log.error("[ERROR] Gagal memulai musik: {}".format(str(e)))
        return

    if res_music.get("code") != 0:
        print("[ERROR] Gagal memutar musik: {}".format(res_music.get("msg")))
        log.error("[ERROR] Gagal memutar musik: {}".format(res_music.get("msg")))
        return

    while True:
        # Cek gestur ThumbsDown di awal siklus mode interaktif
        if interactive:
            try:
                current_gesture = get_current_gesture()
            except Exception as e:
                log.error("[ERROR] Gagal membaca gestur saat dance: {}".format(str(e)))
                current_gesture = ""
            if (current_gesture or "").lower() == "thumbsdown":
                print(
                    "[STOP] Gestur ThumbsDown terdeteksi. Menghentikan mode interaktif...")
                log.info("[STOP] Gestur ThumbsDown terdeteksi. Menghentikan mode interaktif...")
                try:
                    YanAPI.sync_do_tts(tts="Mode interaktif dihentikan.")
                except Exception:
                    pass
                try:
                    YanAPI.stop_play_music()
                except Exception:
                    pass
                break

        music_state = YanAPI.get_media_music_state() or {}
        data = music_state.get("data", {}) or {}

        status = data.get("status", "")
        current_song = data.get("name", "")

        if status != "run" or current_song != music_name:
            print("[STATUS] Musik berhenti! Menghentikan gerakan robot...")
            log.info("[STATUS] Musik berhenti! Menghentikan gerakan robot...")
            YanAPI.stop_play_motion()
            break

        print("[INFO] Mencoba mulai menari: {}".format(motion_name))
        log.info("[INFO] Memutar gerakan: {}".format(motion_name))
        try:
            YanAPI.sync_play_motion(name=motion_name)
        except Exception as e:
            log.error("[ERROR] Gerakan tari gagal: {}".format(str(e)))
            break

        # sync_play_motion blocking; hindari memanggil motion berulang cepat.
        time.sleep(0.5)

    try:
        YanAPI.stop_play_motion()
    except Exception:
        pass
    try:
        YanAPI.sync_play_motion(name="reset")
    except Exception as e:
        log.error("[ERROR] Gagal reset setelah musik: {}".format(str(e)))


# =====================================================================
# LOOP UTAMA INTERAKSI
# =====================================================================
def main_loop_interactive():
    random_dance(interactive=True)


def random_dance(interactive=False):
    no_speech_count = 0
    battery_check_counter = 0
    BATTERY_CHECK_INTERVAL = 10  # Cek baterai setiap 10 iterasi (~15 detik)
    max_iterations = 200  # Safety valve agar loop tidak berjalan selamanya

    iteration = 0
    while iteration < max_iterations:
        iteration += 1

        # Cek baterai hanya setiap BATTERY_CHECK_INTERVAL iterasi
        battery_check_counter += 1
        if battery_check_counter >= BATTERY_CHECK_INTERVAL:
            battery_check_counter = 0
            try:
                batere = YanAPI.get_robot_battery_value()
                if batere >= 0 and batere < BATTERY_LOW_THRESHOLD:
                    print("[PERINGATAN] Baterai rendah ({}%). Lewati gerakan.".format(batere))
                    log.warning("[PERINGATAN] Baterai rendah ({}%). Lewati gerakan.".format(batere))
                    try:
                        YanAPI.set_robot_led(type="button", color="red", mode="blink")
                    except Exception:
                        pass
                    try:
                        YanAPI.sync_do_tts(tts="Baterai saya rendah. Harap diisi daya.")
                    except Exception:
                        pass
                    time.sleep(SCAN_DELAY)
                    continue
            except Exception as e:
                log.error("[ERROR] Gagal membaca baterai: {}".format(str(e)))
                print("[ERROR] Gagal membaca baterai: {}".format(str(e)))

        # Cek gestur ThumbsDown di awal siklus mode interaktif
        if interactive:
            try:
                current_gesture = get_current_gesture()  # Gunakan helper
            except Exception as e:
                log.error("[ERROR] Gagal membaca gestur: {}".format(str(e)))
                current_gesture = ""
            # Pakai .lower()
            if (current_gesture or "").lower() == "thumbsdown":
                print(
                    "[STOP] Gestur ThumbsDown terdeteksi. Menghentikan mode interaktif...")
                log.info("[STOP] Gestur ThumbsDown terdeteksi. Menghentikan mode interaktif...")
                try:
                    YanAPI.sync_do_tts(tts="Mode interaktif dihentikan.")
                except Exception:
                    pass
                try:
                    YanAPI.sync_play_motion(name="reset")
                except Exception:
                    pass
                try:
                    YanAPI.stop_play_music()
                except Exception:
                    pass

                break

        try:
            YanAPI.set_robot_led(type="button", color="white", mode="blink")
        except Exception as e:
            log.error("[ERROR] Gagal set LED: {}".format(str(e)))
        print("\n[MEMINDAI] Mencari wajah manusia di depan kamera...")
        log.info("[MEMINDAI] Mencari wajah manusia...")

        try:
            face_count = YanAPI.sync_do_face_recognition_value(type="quantity")
            if isinstance(face_count, dict):
                data = face_count.get("data")
                if isinstance(data, dict):
                    face_count = data.get("quantity", 0)
                else:
                    face_count = data or 0
            face_count = int(face_count or 0)
        except (TypeError, ValueError) as e:
            log.error("[ERROR] Nilai jumlah wajah tidak valid: {}".format(str(e)))
            face_count = 0
        except Exception as e:
            log.error("[ERROR] Gagal deteksi wajah: {}".format(str(e)))
            face_count = 0

        if face_count and face_count > 0:
            print("[TERDETEKSI] Menemukan {} wajah manusia!".format(face_count))
            log.info("[TERDETEKSI] {} wajah terdeteksi.".format(face_count))

            try:
                gender = YanAPI.sync_do_face_recognition_value(type="gender")
            except Exception as e:
                log.error("[ERROR] Gagal deteksi gender: {}".format(str(e)))
                gender = ""

            try:
                expression = YanAPI.sync_do_face_recognition_value(type="expression")
            except Exception as e:
                log.error("[ERROR] Gagal deteksi ekspresi: {}".format(str(e)))
                expression = ""
            if isinstance(expression, dict):
                data = expression.get("data")
                if isinstance(data, dict):
                    expression = data.get("expression", "")
                else:
                    expression = data or ""
            expression = str(expression or "none").lower()
            expression_label = EXPRESSION_LABELS.get(expression, "")
            print("[EKSPRESI] {} ({})".format(expression, expression_label or "tanpa konteks mood"))
            log.info("[EKSPRESI] {} ({})".format(expression, expression_label or "tanpa konteks mood"))

            panggilan = "Kakak"
            if isinstance(gender, dict):
                data = gender.get("data")
                if isinstance(data, dict):
                    gender = data.get("gender", "")
                else:
                    gender = data or ""
            gender = str(gender or "").lower()
            if gender == "male":
                panggilan = "Tuan"
            elif gender == "female":
                panggilan = "Nyonya"

            sapaan_list = {
                "happy": [
                    "Wah, {}! Senyumnya membuat hariku bercahaya!",
                    "Halo {}! Senang sekali melihat Anda dalam keadaan gembira hari ini!",
                ],
                "sad": [
                    "Halo {}... Tampaknya Anda sedang sedih. Saya di sini untuk Anda.",
                    "Hai {}... Ada yang membuat hari Anda berat? Ceritakan kepada saya.",
                ],
                "anger": [
                    "Halo {}. Mari kita tarik napas bersama. Saya siap mendengarkan.",
                    "Hai {}. Saya di sini untuk membantu meredakan hati Anda.",
                ],
                "disgust": [
                    "Halo {}. Maafkan saya jika ada yang tidak berkenan.",
                    "Hai {}. Ada yang perlu diperbaiki? Bilang saja kepada saya.",
                ],
                "fear": [
                    "Halo {}. Jangan takut, saya di sini untuk menjaga Anda.",
                    "Hai {}. Tenanglah, Anda aman bersamaku.",
                ],
                "surprised": [
                    "Halo {}! Wah, tampak Anda terkejut. Ada yang menarik hari ini?",
                    "Hai {}! Senyum kejutan itu menarik! Apa yang terjadi?",
                ],
            }
            sapaan_default = [
                "Halo {}! Senang melihat Anda di sini.",
                "Hai {}! Saya robot Yanshee AI, ada yang bisa saya bantu?",
                "Selamat hari ini {}! Apa yang ingin kita diskusikan kali ini?"
            ]
            sapaan_terpilih = random.choice(
                sapaan_list.get(expression, sapaan_default)).format(panggilan)

            try:
                YanAPI.set_robot_led(type="button", color="green", mode="breath")
                YanAPI.sync_play_motion(name="wave", direction="left")
                YanAPI.sync_play_motion(name="reset")
                YanAPI.sync_do_tts(tts=sapaan_terpilih)
            except Exception as e:
                log.error("[ERROR] Gagal sapaan/gerakan: {}".format(str(e)))

            print(
                "[MENDENGAR] Mikrofon aktif, mendengarkan suara {}...".format(panggilan))
            log.info("[MENDENGAR] Mikrofon aktif untuk {}.".format(panggilan))
            try:
                user_speech = YanAPI.sync_do_voice_iat_value()
            except Exception as e:
                log.error("[ERROR] Gagal IAT (suara): {}".format(str(e)))
                user_speech = ""

            if user_speech and len(user_speech.strip()) > 0:
                no_speech_count = 0
                print("[SUARA PENGGUNA]: {}".format(user_speech))
                log.info("[SUARA PENGGUNA]: {}".format(user_speech))

                try:
                    YanAPI.set_robot_led(type="button", color="blue", mode="blink")
                except Exception:
                    pass

                try:
                    ai_response, is_fallback = ask_ollama_cloud(
                        user_speech, panggilan, expression_label)
                except Exception as e:
                    log.error("[ERROR] Gagal memanggil cloud: {}".format(str(e)))
                    ai_response, is_fallback = FALLBACK_TTS, True
                print("[RESPONSE AI]: {}".format(ai_response))
                log.info("[RESPONSE AI] fallback={}: {}".format(is_fallback, ai_response))

                try:
                    YanAPI.set_robot_led(
                        type="button", color="green", mode="breath")
                    YanAPI.sync_do_tts(tts=ai_response)
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
                    finally:
                        try:
                            YanAPI.sync_play_motion(name="reset")
                        except Exception as e:
                            log.error("[ERROR] Gagal reset fallback: {}".format(str(e)))

            else:
                no_speech_count += 1
                print(
                    "[INFO] Tidak ada suara terdeteksi. Hitungan tanpa suara: {}/{}".format(no_speech_count, NO_SPEECH_LIMIT))
                log.info("[INFO] Tidak ada suara. Hitungan: {}/{}".format(no_speech_count, NO_SPEECH_LIMIT))

                if no_speech_count >= NO_SPEECH_LIMIT:
                    print("[AKSI] 3x tidak bersuara! Robot berjalan ke depan...")
                    log.info("[AKSI] 3x ketidakber suara, berputar kanan 3 langkah.")
                    try:
                        YanAPI.sync_do_tts(
                            tts="Tidak ada suara. Saya akan berjalan.")
                        YanAPI.sync_play_motion(
                            name="turn around", direction="left", repeat=3)
                        YanAPI.sync_play_motion(name="reset")
                    except Exception as e:
                        log.error("[ERROR] Gagal gerakan 3-strike: {}".format(str(e)))
                    no_speech_count = 0

            print("[INTERAKSI SELESAI] Memberikan jeda sebelum memindai ulang...")
            log.info("[INTERAKSI SELESAI] Jeda {} detik.".format(POST_INTERACTION_DELAY))
            time.sleep(POST_INTERACTION_DELAY)

        else:
            print(
                "[TIDAK TERDETEKSI] Wajah tidak ditemukan. Menjalankan rutinitas alternatif...")
            log.info("[TIDAK TERDETEKSI] Tidak ada wajah, jalankan rutinitas alternatif.")
            no_speech_count = 0

            try:
                print("-> Belok/Putar kanan 3x")
                YanAPI.sync_play_motion(
                    name="turn around", direction="right", repeat=3)

                print("-> Membungkuk (bow)")
                YanAPI.sync_play_motion(name="bow")

                print("-> Jongkok (crouch)")
                YanAPI.sync_play_motion(name="crouch")
            except Exception as e:
                log.error("[ERROR] Gagal rutinitas alternatif: {}".format(str(e)))

            if daftar_lagu:
                lagu_terpilih = random.choice(daftar_lagu)
                print("-> Memutar lagu acak & joget:", lagu_terpilih)
                log.info("-> Memutar lagu & joget: {}".format(lagu_terpilih))
                try:
                    play_music_and_loop_motion_fast_stop(lagu_terpilih, "joget", interactive=interactive)
                except Exception as e:
                    log.error("[ERROR] Gagal memutar musik/joget: {}".format(str(e)))
            else:
                log.warning("[MUSIK] Daftar lagu kosong; melewati dance musik.")

            try:
                print("-> Reset posisi")
                YanAPI.sync_play_motion(name="reset")
            except Exception as e:
                log.error("[ERROR] Gagal reset posisi: {}".format(str(e)))

        time.sleep(SCAN_DELAY)

    if iteration >= max_iterations:
        print("[PERINGATAN] random_dance mencapai batas maksimum iterasi. Keluar dari loop.")
        log.warning("[PERINGATAN] random_dance mencapai batas maksimum iterasi ({}). Keluar.".format(max_iterations))


def get_current_gesture():
    """Ambil nama gesture dari response YanAPI dalam beberapa format umum."""
    res = YanAPI.sync_do_gesture_recognition()
    if isinstance(res, str):
        return res
    if not isinstance(res, dict) or res.get("code") not in (None, 0):
        return ""
    data = res.get("data")
    if isinstance(data, str):
        return data
    if isinstance(data, dict):
        return data.get("gesture", "") or data.get("name", "") or ""
    return ""


# =====================================================================
# GESTURE CONTROLLER (ENTRY POINT)
# =====================================================================
def gesture_control_loop():
    print("[INIT] Menghubungkan ke robot Yanshee...")
    log.info("[INIT] Menghubungkan ke robot Yanshee di {}".format(ROBOT_IP))
    try:
        YanAPI.yan_api_init(ROBOT_IP)
    except Exception as e:
        log.error("[ERROR] Gagal inisialisasi YanAPI: {}".format(str(e)))
        print("[ERROR] Gagal inisialisasi YanAPI: {}".format(str(e)))
        return

    try:
        YanAPI.sync_do_tts(
            tts="Sistem pengenal gestur tangan siap. Tunjukkan jempol ke atas untuk memulai.")
    except Exception as e:
        log.error("[ERROR] Gagal TTS inisialisasi: {}".format(str(e)))

    while True:
        try:
            YanAPI.set_robot_led(type="button", color="yellow", mode="blink")
        except Exception as e:
            log.error("[ERROR] Gagal set LED: {}".format(str(e)))
        print("\n[GESTURE SCAN] Memindai gestur tangan via kamera...")
        log.debug("[GESTURE SCAN] Memindai gestur tangan...")

        try:
            gesture = get_current_gesture()
        except Exception as e:
            log.error("[ERROR] Gagal membaca gestur: {}".format(str(e)))
            gesture = ""

        if gesture:
            print("[GESTURE CONTROL TERDETEKSI]: {}".format(gesture))
            log.info("[GESTURE CONTROL TERDETEKSI]: {}".format(gesture))
            # Normalisasi ke huruf kecil
            gesture_lower = (gesture or "").lower()

            if gesture_lower == "thumbsup":
                print("[AKSI] Gestur ThumbsUp terdeteksi! Memulai interaksi AI...")
                log.info("[AKSI] ThumbsUp terdeteksi, memulai mode interaktif.")
                try:
                    YanAPI.set_robot_led(
                        type="button", color="green", mode="breath")
                    YanAPI.sync_do_tts(
                        tts="Gestur jempol atas terdeteksi. Memulai mode interaktif.")
                except Exception as e:
                    log.error("[ERROR] Gagal TTS/LED thumbsup: {}".format(str(e)))
                try:
                    main_loop_interactive()
                except Exception as e:
                    log.error("[ERROR] Gagal main_loop_interactive: {}".format(str(e)))

            elif gesture_lower == "thumbsdown":
                print("[AKSI] Gestur ThumbsDown terdeteksi! Robot dalam posisi Idle.")
                log.info("[AKSI] ThumbsDown terdeteksi, robot idle.")
                try:
                    YanAPI.set_robot_led(type="button", color="red", mode="breath")
                    YanAPI.sync_do_tts(tts="Robot kembali ke posisi idle.")
                    YanAPI.sync_play_motion(name="reset")
                    YanAPI.stop_play_music()
                except Exception as e:
                    log.error("[ERROR] Gagal idle sequence: {}".format(str(e)))
                time.sleep(2)

        time.sleep(GESTURE_SCAN_DELAY)


def shutdown_robot():
    try:
        YanAPI.stop_play_music()
    except Exception:
        pass
    try:
        YanAPI.stop_play_motion()
    except Exception:
        pass
    try:
        YanAPI.sync_play_motion(name="reset")
    except Exception:
        pass
    try:
        YanAPI.set_robot_led(type="button", color="red", mode="breath")
    except Exception:
        pass


if __name__ == "__main__":
    try:
        gesture_control_loop()
    except KeyboardInterrupt:
        print("\n[EXIT] Dihentikan pengguna. Mengembalikan robot ke posisi aman...")
        log.info("[EXIT] Dihentikan pengguna, shutdown robot.")
        shutdown_robot()
