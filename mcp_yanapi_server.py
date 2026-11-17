# coding=UTF-8
"""MCP server yang meng-export YanAPI functions sebagai tools.

Menggunakan MCP Python SDK (low-level Server) agar schema parameter
dibangun dari YANAPI_TOOLS dan panggilan blocking dijalankan di
thread pool.

Penggunaan:
    python3 mcp_yanapi_server.py [--robot-ip 127.0.0.1] [--log-level INFO]

Fitur:
    - Exposes sync_play_motion, start_play_motion, sync_play_music, sync_do_tts, dll.
    - Semua tools menggunakan signature YanAPI asli (args dari YanAPI.py docstrings)
    - Blocking calls dijalankan di thread pool (asyncio.to_thread)
"""

import sys
import argparse
import asyncio
import json
import logging
from typing import Dict, Any, List

# Tambahkan path robot_yanshee agar bisa import YanAPI
ROBOT_YANSHSEE_DIR = "/home/tovi/Dokumen/pythonKode/robot_yanshee"
if ROBOT_YANSHSEE_DIR not in sys.path:
    sys.path.insert(0, ROBOT_YANSHSEE_DIR)

import YanAPI
from YanAPI import yan_api_init

# Konfigurasi logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("mcp_yanapi")

try:
    from mcp.server.lowlevel.server import Server
    from mcp.server.stdio import stdio_server
    from mcp import types as mcp_types
except ImportError:
    logger.error("MCP SDK tidak terinstal. Install dengan: pip install 'mcp<2'")
    sys.exit(1)

# Inisialisasi server
server = Server("yanapi")


# Mapping YanAPI functions ke tool names yang clean
YANAPI_TOOLS: Dict[str, Dict[str, Any]] = {
    "sync_play_motion": {
        "func": YanAPI.sync_play_motion,
        "description": "Execute a robot motion and wait for completion",
        "params": {
            "name": {"type": "string", "description": "Motion name (raise, crouch, stretch, come on, wave, bend, walk, turn around, head, bow, reset, joget)"},
            "direction": {"type": "string", "description": "Direction (left/right/both/forward/backward, empty untuk tidak ada)", "default": ""},
            "speed": {"type": "string", "description": "Speed (very slow, slow, normal, fast, very fast)", "default": "normal"},
            "repeat": {"type": "integer", "description": "Repeat count (1-100)", "default": 1},
            "version": {"type": "string", "description": "Motion version (v1/v2)", "default": "v1"},
        },
    },
    "start_play_motion": {
        "func": YanAPI.start_play_motion,
        "description": "Start a robot motion (non-blocking)",
        "params": {
            "name": {"type": "string", "description": "Motion name"},
            "direction": {"type": "string", "description": "Direction (empty untuk tidak ada)", "default": ""},
            "speed": {"type": "string", "description": "Speed", "default": "normal"},
            "repeat": {"type": "integer", "description": "Repeat count", "default": 1},
            "version": {"type": "string", "description": "Motion version", "default": "v1"},
        },
    },
    "sync_play_music": {
        "func": YanAPI.sync_play_music,
        "description": "Play music and wait for completion",
        "params": {
            "name": {"type": "string", "description": "Music file name (e.g. SorrySorry.mp3)", "default": ""},
        },
    },
    "start_play_music": {
        "func": YanAPI.start_play_music,
        "description": "Start playing music (non-blocking)",
        "params": {
            "name": {"type": "string", "description": "Music file name", "default": ""},
        },
    },
    "stop_play_music": {
        "func": YanAPI.stop_play_music,
        "description": "Stop playing music",
        "params": {},
    },
    "sync_do_tts": {
        "func": YanAPI.sync_do_tts,
        "description": "Text-to-speech and wait for completion",
        "params": {
            "tts": {"type": "string", "description": "Text to speak"},
            "interrupt": {"type": "boolean", "description": "Interrupt current speech", "default": True},
        },
    },
    "sync_do_voice_iat_value": {
        "func": YanAPI.sync_do_voice_iat_value,
        "description": "Speech recognition (voice to text)",
        "params": {},
    },
    "sync_set_led": {
        "func": YanAPI.sync_set_led,
        "description": "Set LED color and mode",
        "params": {
            "type": {"type": "string", "description": "LED type (button/camera)"},
            "color": {"type": "string", "description": "Color (white/red/green/blue/yellow/purple/cyan)"},
            "mode": {"type": "string", "description": "Mode (on/off/blink/breath)"},
        },
    },
    "sync_do_motion_gait": {
        "func": YanAPI.sync_do_motion_gait,
        "description": "Execute gait motion and wait for completion",
        "params": {
            "speed_v": {"type": "integer", "description": "Vertical speed (-5 to 5)", "default": 0},
            "speed_h": {"type": "integer", "description": "Horizontal speed (-5 to 5)", "default": 0},
            "steps": {"type": "integer", "description": "Number of steps (0 = 1 billion)", "default": 0},
            "period": {"type": "integer", "description": "Period (0-5)", "default": 1},
            "wave": {"type": "boolean", "description": "Enable arm swing", "default": False},
        },
    },
    "sync_do_face_recognition_value": {
        "func": YanAPI.sync_do_face_recognition_value,
        "description": "Face recognition (returns gender/expression/quantity)",
        "params": {
            "type": {"type": "string", "description": "Task type (recognition, quantity, age_group, gender, age, expression, mask, glass)"},
        },
    },
    "get_robot_battery_value": {
        "func": YanAPI.get_robot_battery_value,
        "description": "Get battery percentage (0-100)",
        "params": {},
    },
    "get_robot_volume_value": {
        "func": YanAPI.get_robot_volume_value,
        "description": "Get robot volume (0-100)",
        "params": {},
    },
    "get_motion_list_value": {
        "func": YanAPI.get_motion_list_value,
        "description": "Get list of available motions",
        "params": {},
    },
    "get_media_music_list": {
        "func": YanAPI.get_media_music_list,
        "description": "Get list of available music files",
        "params": {},
    },
    "sync_set_servo_rotate": {
        "func": YanAPI.sync_set_servo_rotate,
        "description": "Set servo angles and wait for completion",
        "params": {
            "angles": {"type": "object", "description": "Map of servo name to angle (0-180)"},
            "runtime": {"type": "integer", "description": "Runtime in ms", "default": 200},
        },
    },
    "sync_do_QR_code_recognition": {
        "func": YanAPI.sync_do_QR_code_recognition,
        "description": "QR code recognition with timeout",
        "params": {
            "timeOut": {"type": "integer", "description": "Timeout in seconds (<=0 = infinite)", "default": 8},
        },
    },
}


def _build_schema(tool_info: Dict[str, Any]) -> Dict[str, Any]:
    properties = {}
    required = []
    for name, info in (tool_info.get("params") or {}).items():
        prop = {"type": info.get("type", "string"), "description": info.get("description", "")}
        if "default" in info:
            prop["default"] = info["default"]
        else:
            required.append(name)
        properties[name] = prop
    schema = {"type": "object", "properties": properties}
    if required:
        schema["required"] = required
    return schema


@server.list_tools()
async def _list_tools() -> List[mcp_types.Tool]:
    result = []
    for name, info in YANAPI_TOOLS.items():
        result.append(mcp_types.Tool(
            name=name,
            description=info["description"],
            inputSchema=_build_schema(info),
        ))
    return result


@server.call_tool()
async def _call_tool(name: str, arguments: Dict[str, Any]) -> List[mcp_types.TextContent]:
    tool_info = YANAPI_TOOLS.get(name)
    if tool_info is None:
        return [mcp_types.TextContent(type="text", text=json.dumps({"error": "Unknown tool: {}".format(name)}))]

    func = tool_info["func"]
    kwargs = {k: v for k, v in (arguments or {}).items() if v is not None}
    try:
        result = await asyncio.to_thread(func, **kwargs)
        text = json.dumps(result, ensure_ascii=False, default=str)
    except Exception as e:
        logger.error("Error calling %s: %s", name, str(e))
        text = json.dumps({"error": str(e)})
    return [mcp_types.TextContent(type="text", text=text)]


async def _main_async(robot_ip: str):
    yan_api_init(robot_ip)
    logger.info("Starting YanAPI MCP server (stdio)...")
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main():
    parser = argparse.ArgumentParser(description="YanAPI MCP Server (stdio)")
    parser.add_argument("--robot-ip", default="127.0.0.1", help="Robot IP address")
    parser.add_argument("--log-level", default="INFO", help="Log level")
    args = parser.parse_args()

    logging.getLogger().setLevel(getattr(logging, args.log_level.upper(), logging.INFO))

    logger.info("Initializing YanAPI with robot IP: %s", args.robot_ip)
    try:
        asyncio.run(_main_async(args.robot_ip))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
