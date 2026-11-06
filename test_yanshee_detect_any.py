"""Tests for ask_ollama_cloud() in yanshee_detect_any.py.

Run with: python3 -m unittest test_yanshee_detect_any -v
"""
import json
import os
import sys
import types
import unittest
from unittest.mock import MagicMock, patch

# Inject a fake YanAPI before importing the module under test.
_fake_yanapi = types.ModuleType("YanAPI")
_fake_yanapi.yan_api_init = lambda *a, **k: None
_fake_yanapi.sync_do_tts = lambda *a, **k: None
_fake_yanapi.set_robot_led = lambda *a, **k: None
_fake_yanapi.sync_play_motion = lambda *a, **k: True
_fake_yanapi.sync_do_gesture_recognition = lambda: {}
_fake_yanapi.sync_do_face_recognition_value = lambda *a, **k: {}
_fake_yanapi.sync_do_voice_iat_value = lambda *a, **k: ""
_fake_yanapi.stop_play_music = lambda *a, **k: None
_fake_yanapi.stop_play_motion = lambda *a, **k: None
_fake_yanapi.get_media_music_state = lambda *a, **k: {}
sys.modules["YanAPI"] = _fake_yanapi

import yanshee_detect_any as yda  # noqa: E402


def _make_response(body):
    resp = MagicMock()
    resp.read.return_value = json.dumps(body).encode("utf-8")
    resp.__enter__ = lambda self: self
    resp.__exit__ = lambda self, *a: False
    return resp


class TestAskOllamaCloud(unittest.TestCase):
    def setUp(self):
        self._orig_api_key = yda.API_KEY
        yda.API_KEY = "test-key"

    def tearDown(self):
        yda.API_KEY = self._orig_api_key

    def test_no_api_key_returns_fallback(self):
        yda.API_KEY = ""
        text, fallback = yda.ask_ollama_cloud("hi", "pria")
        self.assertTrue(fallback)
        self.assertEqual(text, yda.FALLBACK_TTS)

    @patch("urllib.request.urlopen")
    def test_plain_content_success(self, mock_urlopen):
        mock_urlopen.return_value = _make_response(
            {"choices": [{"message": {"content": "Halo!"}}]}
        )
        text, fallback = yda.ask_ollama_cloud("hi", "pria")
        self.assertFalse(fallback)
        self.assertEqual(text, "Halo!")

    @patch("urllib.request.urlopen")
    def test_empty_choices_returns_fallback(self, mock_urlopen):
        mock_urlopen.return_value = _make_response({"choices": []})
        text, fallback = yda.ask_ollama_cloud("hi", "pria")
        self.assertTrue(fallback)
        self.assertEqual(text, yda.FALLBACK_TTS)

    @patch("urllib.request.urlopen")
    def test_empty_content_returns_fallback(self, mock_urlopen):
        mock_urlopen.return_value = _make_response(
            {"choices": [{"message": {"content": "   "}}]}
        )
        text, fallback = yda.ask_ollama_cloud("hi", "pria")
        self.assertTrue(fallback)
        self.assertEqual(text, yda.FALLBACK_TTS)

    @patch("urllib.request.urlopen")
    def test_http_error_returns_fallback(self, mock_urlopen):
        import urllib.error

        mock_urlopen.side_effect = urllib.error.HTTPError(
            yda.OLLAMA_CLOUD_URL, 500, "boom", {}, None
        )
        # HTTPError.read must return bytes
        mock_urlopen.side_effect.read = lambda: b"boom"
        text, fallback = yda.ask_ollama_cloud("hi", "pria")
        self.assertTrue(fallback)
        self.assertEqual(text, yda.FALLBACK_TTS)

    @patch("urllib.request.urlopen")
    def test_generic_exception_returns_fallback(self, mock_urlopen):
        mock_urlopen.side_effect = RuntimeError("network down")
        text, fallback = yda.ask_ollama_cloud("hi", "pria")
        self.assertTrue(fallback)
        self.assertEqual(text, yda.FALLBACK_TTS)

    @patch("urllib.request.urlopen")
    def test_tool_call_move_robot_success(self, mock_urlopen):
        mock_urlopen.return_value = _make_response(
            {
                "choices": [
                    {
                        "message": {
                            "tool_calls": [
                                {
                                    "function": {
                                        "name": "move_robot",
                                        "arguments": json.dumps({"action": "wave"}),
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
        )
        text, fallback = yda.ask_ollama_cloud("wave", "pria")
        self.assertFalse(fallback)
        self.assertEqual(text, "Saya sudah melakukan gerakan wave untuk Anda!")

    @patch("urllib.request.urlopen")
    def test_tool_call_move_robot_invalid_action(self, mock_urlopen):
        mock_urlopen.return_value = _make_response(
            {
                "choices": [
                    {
                        "message": {
                            "tool_calls": [
                                {
                                    "function": {
                                        "name": "move_robot",
                                        "arguments": json.dumps({"action": "dance"}),
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
        )
        text, fallback = yda.ask_ollama_cloud("dance", "pria")
        self.assertFalse(fallback)
        self.assertEqual(text, "Maaf, gerakan dance gagal dilakukan.")

    @patch("urllib.request.urlopen")
    def test_tool_call_move_robot_sync_motion_fails(self, mock_urlopen):
        yda.YanAPI.sync_play_motion = lambda *a, **k: (_ for _ in ()).throw(
            RuntimeError("motion fail")
        )
        mock_urlopen.return_value = _make_response(
            {
                "choices": [
                    {
                        "message": {
                            "tool_calls": [
                                {
                                    "function": {
                                        "name": "move_robot",
                                        "arguments": json.dumps({"action": "wave"}),
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
        )
        text, fallback = yda.ask_ollama_cloud("wave", "pria")
        self.assertFalse(fallback)
        self.assertEqual(text, "Maaf, gerakan wave gagal dilakukan.")
        # restore
        yda.YanAPI.sync_play_motion = lambda *a, **k: True

    @patch("urllib.request.urlopen")
    def test_tool_call_invalid_json_arguments_continues(self, mock_urlopen):
        mock_urlopen.return_value = _make_response(
            {
                "choices": [
                    {
                        "message": {
                            "tool_calls": [
                                {
                                    "function": {
                                        "name": "move_robot",
                                        "arguments": "not-json",
                                    }
                                }
                            ],
                            "content": "fallback content",
                        }
                    }
                ]
            }
        )
        text, fallback = yda.ask_ollama_cloud("hi", "pria")
        self.assertFalse(fallback)
        self.assertEqual(text, "fallback content")

    @patch("urllib.request.urlopen")
    def test_non_move_robot_tool_call_falls_to_content(self, mock_urlopen):
        mock_urlopen.return_value = _make_response(
            {
                "choices": [
                    {
                        "message": {
                            "tool_calls": [
                                {
                                    "function": {
                                        "name": "other_tool",
                                        "arguments": "{}",
                                    }
                                }
                            ],
                            "content": "hello",
                        }
                    }
                ]
            }
        )
        text, fallback = yda.ask_ollama_cloud("hi", "pria")
        self.assertFalse(fallback)
        self.assertEqual(text, "hello")

    @patch("urllib.request.urlopen")
    def test_message_missing_returns_fallback(self, mock_urlopen):
        mock_urlopen.return_value = _make_response(
            {"choices": [{"no_message": True}]}
        )
        text, fallback = yda.ask_ollama_cloud("hi", "pria")
        self.assertTrue(fallback)
        self.assertEqual(text, yda.FALLBACK_TTS)


if __name__ == "__main__":
    unittest.main()
