# Dynamic Tool Creation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Menambahkan kemampuan pembuatan tool dinamis untuk rutinitas gerakan robot Yanshee oleh LLM dengan persistensi JSON.

**Architecture:** Modul terpisah `routine_manager.py` menangani validasi langkah gerakan, serialisasi, dan pemuatan `custom_tools.json`. Skrip `yanshee_detect_any.py` mendaftarkan meta-tool `create_motion_routine`, memuat rutinitas tersimpan saat startup, dan mengeksekusi langkah-langkah secara berurutan.

**Tech Stack:** Python 3.5+ (Standard Library: `json`, `os`, `time`, `re`, `unittest`), YanAPI.

**Spec:** `docs/superpowers/specs/2026-11-05-dynamic-tool-creation-design.md`

## Global Constraints
- Kompatibel dengan Python 3.5: gunakan `urllib`, `json`, `.format()`; tanpa f-string atau `dataclass`.
- Jangan ubah file biner robot atau `YanAPI.py` / `lib_ukit/`.
- Validasi ketat nama aksi harus anggota `VALID_ACTIONS` dan arah harus valid untuk aksi terkait.

## Review Focus
- Aksi tidak dikenal dalam `steps`: ditolak dan pesan error jelas dikembalikan ke LLM.
- Format `custom_tools.json` korup atau kosong: dimuat dengan aman tanpa menyebabkan skrip crash.
- Nilai `repeat` atau `delay` di luar batas wajar: dinormalisasi (repeat: 1–100, delay: 0.0–10.0 detik).
- Duplikasi nama tool: nama yang sudah ada diperbarui atau ditolak secara konsisten.
- Argumen `arguments` dari LLM berupa dict langsung (bukan string JSON): diproses tanpa error `json.loads`.

---

### Task 1: Modul Manajemen Rutinitas `routine_manager.py` dan Unit Test

**Files:**
- Create: `routine_manager.py`
- Test: `test_routine_manager.py`

**Interfaces:**
- Produces:
  - `validate_routine(name, description, steps, valid_actions, action_directions) -> (bool, str, list)`
  - `load_custom_routines(filepath) -> dict`
  - `save_custom_routine(name, description, steps, filepath) -> (bool, str)`

- [ ] **Step 1: Tulis unit test untuk validasi dan persistensi rutinitas**

```python
# test_routine_manager.py
import unittest
import os
import json
from routine_manager import validate_routine, load_custom_routines, save_custom_routine

class TestRoutineManager(unittest.TestCase):
    def setUp(self):
        self.test_json = "test_custom_tools.json"
        self.valid_actions = ["wave", "bow", "crouch", "reset", "walk", "raise", "turn around", "joget"]
        self.action_directions = {
            "raise": ("left", "right", "both"),
            "wave": ("left", "right", "both"),
            "walk": ("forward", "backward", "left", "right"),
            "turn around": ("left", "right"),
        }

    def tearDown(self):
        if os.path.exists(self.test_json):
            os.remove(self.test_json)

    def test_validate_valid_routine(self):
        steps = [
            {"action": "wave", "direction": "left", "repeat": 2, "delay": 0.5},
            {"action": "bow", "direction": "", "repeat": 1, "delay": 0.0}
        ]
        ok, msg, clean_steps = validate_routine("salam_hormat", "Memberi salam", steps, self.valid_actions, self.action_directions)
        self.assertTrue(ok)
        self.assertEqual(len(clean_steps), 2)
        self.assertEqual(clean_steps[0]["repeat"], 2)

    def test_validate_invalid_action(self):
        steps = [{"action": "terbang", "direction": "", "repeat": 1}]
        ok, msg, _ = validate_routine("terbang_tinggi", "Terbang", steps, self.valid_actions, self.action_directions)
        self.assertFalse(ok)
        self.assertIn("terbang", msg)

    def test_save_and_load_routine(self):
        steps = [{"action": "bow", "direction": "", "repeat": 1, "delay": 0.5}]
        ok, _ = save_custom_routine("hormat", "Membungkuk", steps, self.test_json)
        self.assertTrue(ok)
        routines = load_custom_routines(self.test_json)
        self.assertIn("hormat", routines)
        self.assertEqual(routines["hormat"]["steps"][0]["action"], "bow")
```

- [ ] **Step 2: Jalankan test untuk memastikan test gagal (karena modul belum ada)**

Run: `python3 -m unittest test_routine_manager.py`
Expected: FAIL dengan `ImportError: No module named 'routine_manager'`

- [ ] **Step 3: Implementasikan `routine_manager.py`**

Implementasikan fungsi:
- `validate_routine(name, description, steps, valid_actions, action_directions)`
- `load_custom_routines(filepath="custom_tools.json")`
- `save_custom_routine(name, description, steps, filepath="custom_tools.json")`
Pastikan penanganan exception aman saat membaca/menulis JSON.

- [ ] **Step 4: Jalankan test untuk memastikan lolos**

Run: `python3 -m unittest test_routine_manager.py`
Expected: Ran 3 tests in ... OK

- [ ] **Step 5: Komit modul dan test**

```bash
git add routine_manager.py test_routine_manager.py
git commit -m "feat: tambahkan routine_manager untuk validasi dan persistensi tool dinamis"
```

---

### Task 2: Integrasi Meta-Tool `create_motion_routine` & Loader ke `yanshee_detect_any.py`

**Files:**
- Modify: `yanshee_detect_any.py`
- Test: `test_integration_tools.py`

**Interfaces:**
- Consumes:
  - `routine_manager.load_custom_routines`
  - `routine_manager.save_custom_routine`
  - `routine_manager.validate_routine`
- Produces:
  - Meta-tool `create_motion_routine` di skema `tools`
  - Executor `_execute_create_motion_routine(arguments)`
  - Fungsi `register_custom_routine(routine_def)`
  - Normalisasi gestur `thumbsup/good` dan `thumbsdown/bad`

- [ ] **Step 1: Tulis integration test `test_integration_tools.py`**

```python
# test_integration_tools.py
import unittest
import yanshee_detect_any as yda

class TestToolIntegration(unittest.TestCase):
    def test_meta_tool_registered(self):
        tool_names = [t["function"]["name"] for t in yda.tools]
        self.assertIn("create_motion_routine", tool_names)
        self.assertIn("create_motion_routine", yda.tool_executors)

    def test_create_motion_routine_executor(self):
        args = {
            "name": "salam_dua_tangan",
            "description": "Melambaikan tangan dua arah lalu reset",
            "steps": [
                {"action": "wave", "direction": "both", "repeat": 1, "delay": 0.1},
                {"action": "reset", "direction": "", "repeat": 1, "delay": 0.0}
            ]
        }
        resp, is_fallback = yda.tool_executors["create_motion_routine"](args)
        self.assertFalse(is_fallback)
        self.assertIn("salam_dua_tangan", resp)
        # Pastikan terdaftar di runtime tools
        tool_names = [t["function"]["name"] for t in yda.tools]
        self.assertIn("salam_dua_tangan", tool_names)
        self.assertIn("salam_dua_tangan", yda.tool_executors)
```

- [ ] **Step 2: Jalankan test untuk memverifikasi kegagalan**

Run: `python3 -m unittest test_integration_tools.py`
Expected: FAIL dengan `AssertionError: 'create_motion_routine' not found in [...]`

- [ ] **Step 3: Modifikasi `yanshee_detect_any.py`**
1. Import helper dari `routine_manager.py`.
2. Tambahkan skema meta-tool `create_motion_routine` ke `tools`.
3. Buat executor `_execute_create_motion_routine(arguments)`.
4. Buat fungsi runner `_create_routine_runner(steps)` yang mengeksekusi langkah-langkah secara berurutan dan mengembalikan status.
5. Buat fungsi `register_custom_routine(routine_def)` untuk mendaftarkan tool kustom ke `tools` dan `tool_executors`.
6. Panggil `load_and_register_custom_routines()` saat modul di-load.
7. Tangani argumen dict maupun string JSON di `ask_ollama_cloud()`.
8. Perbaiki normalisasi gestur `gesture_lower in ("thumbsup", "good")` dan `("thumbsdown", "bad")`.

- [ ] **Step 4: Jalankan integration test dan syntax compile**

Run: `python3 -m unittest test_integration_tools.py`
Run: `python3 -m py_compile yanshee_detect_any.py`
Expected: PASS semua test dan compile sukses.

- [ ] **Step 5: Komit perubahan**

```bash
git add yanshee_detect_any.py test_integration_tools.py
git commit -m "feat: integrasikan meta-tool create_motion_routine dan loader di yanshee_detect_any"
```

---

### Task 3: Verifikasi Menyeluruh & Dokumentasi

**Files:**
- Create/Update: `custom_tools.json` (dibuat/diverifikasi)
- Update: `README.md`
- Update: `AGENTS.md`

- [ ] **Step 1: Bersihkan artefak tes sementara**

Hapus file tes seperti `test_custom_tools.json` jika tertinggal.

- [ ] **Step 2: Jalankan seluruh suite tes unit dan kompilasi**

Run: `python3 -m unittest discover -s . -p "test_*.py"`
Run: `python3 -m py_compile yanshee_detect_any.py yanshee_detect.py config.py routine_manager.py`
Expected: PASS tanpa error.

- [ ] **Step 3: Perbarui `README.md` dan `AGENTS.md`**

Dokumentasikan fitur `create_motion_routine` dan persistensi `custom_tools.json`.

- [ ] **Step 4: Komit dokumentasi dan finalisasi**

```bash
git add README.md AGENTS.md
git commit -m "docs: dokumentasikan dynamic tool creation dan custom_tools.json"
```
