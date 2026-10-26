"""Mind Blower: start here.

    python run.py                          normal party
    python run.py --dev --bots 12 --speed 10   test on your own

Then follow what the console prints: open the host link on your phone
first, and the TV screen opens in your browser.
"""
from __future__ import annotations

import argparse
import logging
import secrets
import sys
import threading
import webbrowser
from pathlib import Path

from mindblower.game import Game
from mindblower.network import qr_text
from mindblower.questions import load_questions
from mindblower.server import Server

ROOT = Path(__file__).resolve().parent


def parse_args():
    parser = argparse.ArgumentParser(description="Mind Blower party game server")
    parser.add_argument("--port", type=int, default=5000, help="port to listen on (default 5000)")
    parser.add_argument("--dev", action="store_true", help="dev controls on the TV and the /dev page")
    parser.add_argument("--bots", type=int, default=0, help="number of bot players to add")
    parser.add_argument("--speed", type=float, default=1.0, help="bots act this many times faster")
    parser.add_argument("--no-browser", action="store_true", help="don't open the TV screen automatically")
    parser.add_argument("--questions", default=str(ROOT / "data" / "questions.json"))
    return parser.parse_args()


def clear_old_selfies(folder: Path) -> None:
    """Selfies from a previous party are deleted each time the server starts."""
    folder.mkdir(exist_ok=True)
    for f in folder.iterdir():
        if f.is_file() and f.name != ".gitkeep":
            f.unlink()


def quiet_server_logs() -> None:
    """Hide the web server's request log and banner so the console stays readable."""
    logging.getLogger("werkzeug").setLevel(logging.ERROR)
    import flask.cli
    flask.cli.show_server_banner = lambda *args, **kwargs: None


def main() -> None:
    args = parse_args()
    quiet_server_logs()
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # lets Windows consoles draw the QR code
    except (AttributeError, ValueError):
        pass
    uploads = ROOT / "uploads"
    clear_old_selfies(uploads)

    game = Game(load_questions(args.questions), host_key=secrets.token_hex(3).upper())
    server = Server(game, port=args.port, uploads_dir=uploads, dev=args.dev, bot_speed=args.speed)

    if args.bots:
        server.bots.request(args.bots)
    server.bots.start()

    tv_url = f"http://localhost:{args.port}/tv"
    line = "=" * 64
    print(f"\n{line}\n  MIND BLOWER is running\n{line}")
    print("\n  1. HOST: open this link on your phone FIRST (scan the code below):")
    print(f"     {server.host_url}\n")
    try:
        print(qr_text(server.host_url))
    except UnicodeEncodeError:
        print("     (this console can't draw the QR code, so type the link instead)\n")
    print(f"  2. TV screen (opens automatically on this PC): {tv_url}")
    print(f"  3. Guests scan the QR code on the TV, or go to: {server.join_url}")
    if args.dev:
        print(f"\n  DEV page (TV + 4 phones): http://localhost:{args.port}/dev")
    if args.bots:
        print(f"  {args.bots} bots will join as soon as the host does (speed x{args.speed:g}).")
    print(f"\n  Phones must be on the same Wi-Fi as this PC. Press Ctrl+C to stop.\n{line}\n")

    if not args.no_browser:
        threading.Timer(1.5, webbrowser.open, args=(f"http://localhost:{args.port}/dev" if args.dev else tv_url,)).start()

    server.socketio.run(server.app, host="0.0.0.0", port=args.port,
                        allow_unsafe_werkzeug=True, use_reloader=False, log_output=False)


if __name__ == "__main__":
    main()
