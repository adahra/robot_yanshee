import json
import os
import logging
import sys


DEFAULT_CONFIG = {
    "ROBOT_IP": "127.0.0.1",
    "OLLAMA_CLOUD_URL": "https://ollama.com/v1/chat/completions",
    "MODEL_NAME": "nemotron-3-ultra",
    "REQUEST_TIMEOUT": 30,
    "NO_SPEECH_LIMIT": 3,
    "SCAN_DELAY": 1.5,
    "POST_INTERACTION_DELAY": 5,
    "GESTURE_SCAN_DELAY": 1,
    "BATTERY_LOW_THRESHOLD": 15,
    "VALID_ACTIONS": ["wave", "bow", "walk", "raise", "crouch", "reset", "turn around", "joget"],
    "daftar_lagu": [
        "rollerblade.mp3",
        "ghost.mp3",
        "bojo_galak.mp3",
        "kelingan_mantan.mp3",
        "house.mp3",
        "fukai_mori.mp3",
        "seventeen.mp3",
        "fortune.mp3",
        "cincin.mp3",
        "drop_dead.mp3",
        "uare.mp3",
        "lenka.mp3",
        "sunflower.mp3",
        "hindia.mp3",
        "wind.mp3"
    ],
    "LOG_FILE": "yanshee.log",
    "LOG_LEVEL": "INFO",
    "FALLBACK_MOTION": "reset",
    "FALLBACK_TTS": "Maaf, saya tidak dapat terhubung ke layanan cloud. Silakan coba lagi nanti."
}

_config = None
_logger = None


def load_config(config_path="config.json"):
    """Muat konfigurasi dari file JSON, fallback ke default jika gagal."""
    global _config
    if _config is not None:
        return _config

    config = dict(DEFAULT_CONFIG)
    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                user_config = json.load(f)
            config.update(user_config)
        except (ValueError, IOError) as e:
            print("[CONFIG] Gagal membaca config.json, menggunakan default: {}".format(e))

    # Nilai rusak kembali ke default agar loop robot tidak gagal diam-diam.
    for key in ("REQUEST_TIMEOUT", "NO_SPEECH_LIMIT", "BATTERY_LOW_THRESHOLD"):
        value = config.get(key)
        default = DEFAULT_CONFIG[key]
        if not isinstance(value, (int, float)) or value < 0:
            config[key] = default
    for key in ("SCAN_DELAY", "POST_INTERACTION_DELAY", "GESTURE_SCAN_DELAY"):
        value = config.get(key)
        default = DEFAULT_CONFIG[key]
        if not isinstance(value, (int, float)) or value < 0:
            config[key] = default
    if not isinstance(config.get("VALID_ACTIONS"), list) or not config["VALID_ACTIONS"]:
        config["VALID_ACTIONS"] = list(DEFAULT_CONFIG["VALID_ACTIONS"])
    else:
        config["VALID_ACTIONS"] = [str(action) for action in config["VALID_ACTIONS"] if str(action)]
    if not isinstance(config.get("daftar_lagu"), list):
        config["daftar_lagu"] = list(DEFAULT_CONFIG["daftar_lagu"])
    else:
        config["daftar_lagu"] = [str(song) for song in config["daftar_lagu"] if str(song)]

    _config = config
    return config


def get_config():
    if _config is None:
        return load_config()
    return _config


def setup_logging(config):
    """Siapkan logging ke file dan konsol. Hanya dijalankan sekali."""
    global _logger
    if _logger is not None:
        return _logger

    log_file = config.get("LOG_FILE", "yanshee.log")
    log_level_str = config.get("LOG_LEVEL", "INFO")
    log_level = getattr(logging, log_level_str.upper(), logging.INFO)

    logger = logging.getLogger("yanshee")
    logger.setLevel(log_level)

    # Hindari handler duplikat jika dipanggil berkali-kali
    if not logger.handlers:
        fh = logging.FileHandler(log_file)
        fh.setLevel(log_level)

        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(log_level)

        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)

        logger.addHandler(fh)
        logger.addHandler(ch)

    _logger = logger
    return logger


def get_logger():
    if _logger is None:
        config = get_config()
        return setup_logging(config)
    return _logger
