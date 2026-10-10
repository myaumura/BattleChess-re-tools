#!/usr/bin/env python3
"""Native POSIX PTY integration check of the actual SDL game host."""

import os
import pty
import select
import subprocess
import sys


def read_exact(fd, size):
    """Native test peer: bound waits so host regressions fail instead of hanging."""
    result = b""
    while len(result) < size:
        assert select.select([fd], [], [], 15)[0], "Timed out waiting for host"
        result += os.read(fd, size - len(result))
    return result


def frame(kind, payload=b""):
    """SENDBLOC 0x10ede wire fixture, independent of the native codec."""
    body = bytes([kind, len(payload) + 4]) + payload
    return body + bytes([(0x20 + sum(body[::2])) & 255, (0x30 + sum(body[1::2])) & 255])


def exchange(master, kind, payload=b""):
    """Send one original packet and require its exact acknowledgment."""
    os.write(master, frame(kind, payload))
    assert read_exact(master, 4) == bytes.fromhex("a5 04 c5 34")


def run_case(window_quit):
    """Drive controller selection, original SENDMOVE and CNFGETCO in the SDL host."""
    master, slave = pty.openpty()
    env = dict(os.environ, SDL_VIDEODRIVER="dummy", SDL_AUDIODRIVER="dummy")
    process = subprocess.Popen(
        [
            sys.argv[1],
            "--data",
            sys.argv[2],
            "--serial",
            os.ttyname(slave),
            "--modem-check",
        ]
        + (["--modem-quit-window"] if window_quit else []),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        assert read_exact(master, 4) == b"ATE\r"
        assert read_exact(master, 6) == bytes.fromhex("a2 06 34 14 f6 4a")
        os.write(master, bytes.fromhex("a5 04 c5 34"))
        os.write(master, bytes.fromhex("a2 06 44 64 06 9a"))
        assert read_exact(master, 4) == bytes.fromhex("a5 04 c5 34")
        # Stray promotion must not survive the incoming board or next move.
        exchange(master, 0xA9, bytes([2]))
        board = bytearray(33)
        board[0] = 1  # Black to move: black a2 pawn, white e8 king, black h8 king.
        board[1 + 4] = 0xE0
        board[1 + 28 + 2] = 0x10
        board[1 + 28 + 3] = 0x09
        exchange(master, 0xA1, board)
        exchange(master, 0xA9, bytes([2]))
        exchange(master, 0xA2, bytes([0, 0x10]))
        # Neither a pawn nor an off-board code is a legal promotion choice.
        exchange(master, 0xA9, bytes([6]))
        exchange(master, 0xA9, bytes([255]))
        exchange(master, 0xA9, bytes([3]))
        os.write(master, b"Your Opponent just quit\r")
        assert select.select([process.stdout], [], [], 15)[0]
        assert process.stdout.readline() == b"Remote quit white-first passed\n"
        os.write(master, b"Your Opponent just quit\r")
        goodbye = read_exact(master, 24)
        assert goodbye == b"Your Opponent just quit\r", goodbye
        stdout, stderr = process.communicate(timeout=20)
        assert process.returncode == 0, stderr.decode()
        assert b"Native modem PTY integration passed" in stdout, stdout.decode()
        print(stdout.decode().strip())
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
        os.close(master)
        os.close(slave)


if __name__ == "__main__":
    run_case(False)
    run_case(True)
