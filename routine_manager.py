# -*- coding: utf-8 -*-
"""
routine_manager.py
Modul untuk validasi dan persistensi rutinitas gerakan robot Yanshee (custom tools).
Kompatibel dengan Python 3.5+.
"""

import os
import json
import re

DEFAULT_ROUTINE_FILE = "custom_tools.json"
MIN_REPEAT = 1
MAX_REPEAT = 100
MIN_DELAY = 0.0
MAX_DELAY = 10.0


def validate_routine(name, description, steps, valid_actions, action_directions):
    """
    Validasi definisi rutinitas gerakan sebelum disimpan atau dieksekusi.

    Args:
        name (str): Nama rutinitas (snake_case/identifier).
        description (str): Deskripsi fungsi untuk LLM.
        steps (list): Daftar dictionary langkah aksi.
        valid_actions (iterable): Kumpulan nama aksi yang sah.
        action_directions (dict): Pemetaan aksi ke tuple arah yang sah.

    Returns:
        tuple: (bool success, str message, list clean_steps)
    """
    if not isinstance(name, str):
        return False, "Nama rutinitas harus berupa string", []
    clean_name = name.strip()
    if not clean_name:
        return False, "Nama rutinitas tidak boleh kosong", []
    if not re.match(r"^[a-zA-Z0-9_]+$", clean_name):
        return False, "Nama rutinitas hanya boleh berisi huruf, angka, dan underscore", []

    if not isinstance(description, str):
        return False, "Deskripsi rutinitas harus berupa string", []
    clean_description = description.strip()
    if not clean_description:
        return False, "Deskripsi rutinitas tidak boleh kosong", []

    if not isinstance(steps, (list, tuple)):
        return False, "Daftar langkah (steps) harus berupa list", []
    if len(steps) == 0:
        return False, "Daftar langkah (steps) tidak boleh kosong", []

    clean_steps = []
    valid_actions_set = set(str(a).lower() for a in valid_actions)

    for idx, step in enumerate(steps):
        if not isinstance(step, dict):
            return False, "Langkah ke-{} harus berupa objek/dictionary".format(idx + 1), []

        action_raw = step.get("action")
        if not action_raw or not isinstance(action_raw, str):
            return False, "Langkah ke-{} tidak memiliki nama aksi ('action')".format(idx + 1), []

        action = action_raw.strip().lower()
        if action not in valid_actions_set:
            return False, "Aksi '{}' pada langkah ke-{} tidak dikenal".format(action, idx + 1), []

        direction_raw = step.get("direction", "")
        direction = str(direction_raw).strip().lower() if direction_raw is not None else ""

        if action in action_directions:
            allowed_dirs = tuple(str(d).lower() for d in action_directions[action])
            if direction and direction not in allowed_dirs:
                return (
                    False,
                    "Arah (direction) '{}' tidak valid untuk aksi '{}'. Pilihan: {}".format(
                        direction, action, ", ".join(allowed_dirs)
                    ),
                    [],
                )
        else:
            direction = ""

        # Normalisasi repeat (1-100)
        try:
            repeat_val = int(step.get("repeat", 1))
        except (ValueError, TypeError):
            repeat_val = 1
        if repeat_val < MIN_REPEAT:
            repeat_val = MIN_REPEAT
        elif repeat_val > MAX_REPEAT:
            repeat_val = MAX_REPEAT

        # Normalisasi delay (0.0-10.0 detik)
        try:
            delay_val = float(step.get("delay", 0.0))
        except (ValueError, TypeError):
            delay_val = 0.0
        if delay_val < MIN_DELAY:
            delay_val = MIN_DELAY
        elif delay_val > MAX_DELAY:
            delay_val = MAX_DELAY
        delay_val = round(delay_val, 2)

        clean_steps.append({
            "action": action,
            "direction": direction,
            "repeat": repeat_val,
            "delay": delay_val
        })

    return True, "OK", clean_steps


def load_custom_routines(filepath=DEFAULT_ROUTINE_FILE):
    """
    Memuat rutinitas tersimpan dari berkas JSON. Mengembalikan dict kosong
    jika berkas tidak ada atau format rusak tanpa crash.

    Args:
        filepath (str): Lokasi berkas JSON.

    Returns:
        dict: Pemetaan nama rutinitas ke data rutinitas.
    """
    if not os.path.exists(filepath):
        return {}

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
        return {}
    except Exception:
        return {}


def save_custom_routine(name, description, steps, filepath=DEFAULT_ROUTINE_FILE):
    """
    Menyimpan atau memperbarui rutinitas gerakan ke dalam berkas JSON.

    Args:
        name (str): Nama rutinitas.
        description (str): Deskripsi rutinitas.
        steps (list): Daftar langkah gerakan yang sudah divalidasi.
        filepath (str): Lokasi berkas JSON.

    Returns:
        tuple: (bool success, str message)
    """
    try:
        routines = load_custom_routines(filepath)
        routines[name] = {
            "name": name,
            "description": description,
            "steps": steps
        }

        dir_path = os.path.dirname(filepath)
        if dir_path and not os.path.exists(dir_path):
            os.makedirs(dir_path)

        tmp_path = filepath + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(routines, f, indent=2, ensure_ascii=False)

        os.replace(tmp_path, filepath)
        return True, "Rutinitas '{}' berhasil disimpan".format(name)
    except Exception as e:
        return False, "Gagal menyimpan rutinitas: {}".format(str(e))
