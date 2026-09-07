"""
Tests for scripts/wake_pc.py (project spec section 23). The script is
deliberately standalone (zero dependency on backend/agent, so it can
run from a different device than the one hosting this repo) - imported
here the same way test_agent_retry_logic.py reaches into agent/.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from wake_pc import build_magic_packet, main  # noqa: E402


def test_magic_packet_structure():
    packet = build_magic_packet("AA:BB:CC:DD:EE:FF")
    assert len(packet) == 102  # 6 + 16*6
    assert packet[:6] == b"\xff" * 6
    mac_bytes = bytes.fromhex("AABBCCDDEEFF")
    for i in range(16):
        start = 6 + i * 6
        assert packet[start : start + 6] == mac_bytes


@pytest.mark.parametrize("mac", ["AA:BB:CC:DD:EE:FF", "aa-bb-cc-dd-ee-ff", "AABBCCDDEEFF"])
def test_accepts_common_mac_formats(mac):
    packet = build_magic_packet(mac)
    assert len(packet) == 102


@pytest.mark.parametrize("mac", ["not-a-mac", "AA:BB:CC:DD:EE", "AA:BB:CC:DD:EE:GG", ""])
def test_rejects_invalid_mac(mac):
    with pytest.raises(ValueError):
        build_magic_packet(mac)


def test_cli_rejects_invalid_mac_with_exit_code_1(capsys):
    exit_code = main(["not-a-valid-mac"])
    assert exit_code == 1
    assert "Error" in capsys.readouterr().err


def test_cli_sends_packet_to_loopback_and_reports_success(capsys):
    # Sending to 127.0.0.1 is a real, harmless UDP send that exercises
    # the actual socket code path without touching the real network.
    exit_code = main(["AA:BB:CC:DD:EE:FF", "--broadcast", "127.0.0.1", "--port", "9"])
    assert exit_code == 0
    assert "Magic packet sent" in capsys.readouterr().out
