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
        self.assertEqual(clean_steps[0]["action"], "wave")
        self.assertEqual(clean_steps[0]["direction"], "left")
        self.assertEqual(clean_steps[0]["delay"], 0.5)

    def test_validate_invalid_action(self):
        steps = [{"action": "terbang", "direction": "", "repeat": 1}]
        ok, msg, _ = validate_routine("terbang_tinggi", "Terbang", steps, self.valid_actions, self.action_directions)
        self.assertFalse(ok)
        self.assertIn("terbang", msg)

    def test_validate_invalid_direction(self):
        steps = [{"action": "wave", "direction": "up", "repeat": 1}]
        ok, msg, _ = validate_routine("lambaian_aneh", "Lambai ke atas", steps, self.valid_actions, self.action_directions)
        self.assertFalse(ok)
        self.assertIn("direction", msg.lower())

    def test_validate_invalid_name(self):
        steps = [{"action": "bow", "direction": "", "repeat": 1}]
        ok, msg, _ = validate_routine("", "Deskripsi", steps, self.valid_actions, self.action_directions)
        self.assertFalse(ok)

        ok, msg, _ = validate_routine("nama dengan spasi", "Deskripsi", steps, self.valid_actions, self.action_directions)
        self.assertFalse(ok)

    def test_validate_empty_or_invalid_steps(self):
        ok, msg, _ = validate_routine("kosong", "Deskripsi", [], self.valid_actions, self.action_directions)
        self.assertFalse(ok)

        ok, msg, _ = validate_routine("bukan_list", "Deskripsi", "langkah", self.valid_actions, self.action_directions)
        self.assertFalse(ok)

    def test_validate_normalization_repeat_and_delay(self):
        steps = [
            {"action": "bow", "direction": "", "repeat": -5, "delay": -1.0},
            {"action": "crouch", "direction": "", "repeat": 999, "delay": 25.0}
        ]
        ok, msg, clean_steps = validate_routine("normalisasi", "Tes normalisasi", steps, self.valid_actions, self.action_directions)
        self.assertTrue(ok)
        self.assertEqual(clean_steps[0]["repeat"], 1)
        self.assertEqual(clean_steps[0]["delay"], 0.0)
        self.assertEqual(clean_steps[1]["repeat"], 100)
        self.assertEqual(clean_steps[1]["delay"], 10.0)

    def test_save_and_load_routine(self):
        steps = [{"action": "bow", "direction": "", "repeat": 1, "delay": 0.5}]
        ok, _ = save_custom_routine("hormat", "Membungkuk", steps, self.test_json)
        self.assertTrue(ok)
        routines = load_custom_routines(self.test_json)
        self.assertIn("hormat", routines)
        self.assertEqual(routines["hormat"]["steps"][0]["action"], "bow")

    def test_save_overwrite_existing_routine(self):
        steps1 = [{"action": "bow", "direction": "", "repeat": 1, "delay": 0.5}]
        save_custom_routine("gerak", "Versi 1", steps1, self.test_json)

        steps2 = [{"action": "wave", "direction": "left", "repeat": 2, "delay": 0.0}]
        save_custom_routine("gerak", "Versi 2", steps2, self.test_json)

        routines = load_custom_routines(self.test_json)
        self.assertEqual(routines["gerak"]["description"], "Versi 2")
        self.assertEqual(routines["gerak"]["steps"][0]["action"], "wave")

    def test_load_nonexistent_or_corrupt_file(self):
        # Nonexistent file returns empty dict
        res = load_custom_routines("nonexistent_tools_12345.json")
        self.assertEqual(res, {})

        # Corrupted file returns empty dict without crashing
        with open(self.test_json, "w") as f:
            f.write("corrupted json content { [ ]")
        res = load_custom_routines(self.test_json)
        self.assertEqual(res, {})

if __name__ == "__main__":
    unittest.main()
