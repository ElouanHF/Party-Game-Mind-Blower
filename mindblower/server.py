"""Flask routes and Socket.IO events.

This layer only translates: a tap arrives -> call the Game -> send fresh
views to every screen, plus one-off fx cues to the TV. All game rules live
in game.py.
"""
from __future__ import annotations

import json
import random
import time
import uuid
from pathlib import Path
from typing import Optional

from flask import Flask, abort, jsonify, render_template, request, send_from_directory
from flask_socketio import SocketIO, join_room

from . import config, views
from .bots import BotManager, mark_everything
from .game import Game, GameError
from .network import local_ip, qr_svg
from .timers import start_grace_timer

ROOT = Path(__file__).resolve().parent.parent
LOCAL_ADDRESSES = {"127.0.0.1", "::1", "localhost"}


def sniff_image(data: bytes) -> Optional[str]:
    """File extension from the first bytes, or None if it isn't a supported image."""
    if data.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return None


class Server:
    def __init__(self, game: Game, port: int, uploads_dir: Path, dev: bool = False,
                 bot_speed: float = 1.0, join_host: Optional[str] = None):
        self.game = game
        self.dev = dev
        self.uploads_dir = uploads_dir
        self.join_url = f"http://{join_host or local_ip()}:{port}/"
        self.host_url = f"{self.join_url}?host={game.host_key}"
        self.qr = qr_svg(self.join_url)

        self.app = Flask(__name__, static_folder=str(ROOT / "static"),
                         template_folder=str(ROOT / "templates"))
        self.app.config["MAX_CONTENT_LENGTH"] = config.SELFIE_MAX_BYTES + 64 * 1024
        self.socketio = SocketIO(self.app, async_mode="threading", cors_allowed_origins="*")

        self.tv_sids: dict[str, bool] = {}              # sid -> opened on this PC (has controls)
        self.phone_sids: dict[str, Optional[str]] = {}  # sid -> player id (None = not joined yet)
        self.last_sent: dict[str, str] = {}             # sid -> last view json, to skip repeats

        self.bots = BotManager(game, self.socketio, uploads_dir, self.broadcast, speed=bot_speed)
        self.rng = random.Random()
        self._routes()
        self._events()

    # ---------------------------------------------------------------- sending

    def _send_view(self, sid: str, view: dict, force: bool = False) -> None:
        body = json.dumps(view, sort_keys=True)
        if not force and self.last_sent.get(sid) == body:
            return
        self.last_sent[sid] = body
        self.socketio.emit("view", {**view, "now": int(time.time() * 1000)}, to=sid)

    def broadcast(self, force_sid: Optional[str] = None) -> None:
        """Send every screen its latest view (only if it changed) and the TV its fx cues."""
        g = self.game
        tv_views = {}
        for sid, local in list(self.tv_sids.items()):
            if local not in tv_views:
                tv_views[local] = views.tv_view(g, self.join_url, self.qr, controls=local, dev=self.dev)
            self._send_view(sid, tv_views[local], force=sid == force_sid)
        for sid, pid in list(self.phone_sids.items()):
            self._send_view(sid, views.phone_view(g, pid), force=sid == force_sid)
        fx = g.drain_fx()
        if fx:
            self.socketio.emit("fx", fx, to="tv")

    def run_action(self, action) -> None:
        """Run a game action under the lock; tell the player if it wasn't allowed."""
        with self.game.lock:
            try:
                action()
            except GameError as e:
                self.socketio.emit("oops", {"message": str(e)}, to=request.sid)
            self.broadcast()

    def _me(self) -> str:
        pid = self.phone_sids.get(request.sid)
        if not pid:
            raise GameError("We couldn't find you. Try refreshing the page.")
        return pid

    # ---------------------------------------------------------------- web routes

    def _routes(self) -> None:
        app, g = self.app, self.game

        def is_local() -> bool:
            return request.remote_addr in LOCAL_ADDRESSES

        @app.get("/")
        def phone():
            return render_template("phone.html")

        @app.get("/tv")
        def tv():
            return render_template("tv.html")

        @app.get("/dev")
        def dev_page():
            if not (self.dev and is_local()):
                abort(404)
            return render_template("dev.html", host_key=g.host_key)

        @app.get("/uploads/<path:filename>")
        def uploads(filename):
            return send_from_directory(self.uploads_dir, filename, max_age=3600)

        @app.post("/api/join")
        def api_join():
            name = request.form.get("name", "")
            host_key = request.form.get("host_key") or None
            file = request.files.get("selfie")
            data = file.read() if file else b""
            ext = sniff_image(data)
            if not data:
                return jsonify(error="Please take a selfie first."), 400
            if ext is None:
                return jsonify(error="That photo didn't work. Please try taking it again."), 400
            if len(data) > config.SELFIE_MAX_BYTES:
                return jsonify(error="That photo is too big. Please try again."), 400

            with g.lock:
                try:
                    filename = f"{uuid.uuid4().hex}.{ext}"
                    player = g.join(name, f"/uploads/{filename}", host_key=host_key)
                except GameError as e:
                    return jsonify(error=str(e)), 400
                (self.uploads_dir / filename).write_bytes(data)
                if player.is_host:
                    self.bots._join_waiting()  # bots requested with --bots join now
                self.broadcast()
            return jsonify(player_id=player.id, is_host=player.is_host)

    # ---------------------------------------------------------------- socket events

    def _events(self) -> None:
        sio, g = self.socketio, self.game

        @sio.on("hello")
        def hello(data):
            data = data or {}
            sid = request.sid
            with g.lock:
                if data.get("role") == "tv":
                    self.tv_sids[sid] = request.remote_addr in LOCAL_ADDRESSES
                    join_room("tv")
                else:
                    old = self.phone_sids.get(sid)
                    if old:
                        g.disconnect(old)
                    pid = data.get("player_id")
                    if pid and pid not in g.players:
                        self.socketio.emit("forget", to=sid)  # e.g. the server was restarted
                        pid = None
                    self.phone_sids[sid] = pid
                    if pid:
                        g.connect(pid)
                self.broadcast(force_sid=sid)

        @sio.on("disconnect")
        def disconnect(*_):
            sid = request.sid
            with g.lock:
                self.tv_sids.pop(sid, None)
                self.last_sent.pop(sid, None)
                pid = self.phone_sids.pop(sid, None)
                if pid:
                    g.disconnect(pid)
                self.broadcast()

        @sio.on("pick")
        def pick(data):
            self.run_action(lambda: g.pick_category(self._me(), data.get("category")))

        @sio.on("skip")
        def skip(data):
            self.run_action(lambda: g.skip(self._me(), data.get("assignment_id")))

        @sio.on("answer")
        def answer(data):
            self.run_action(lambda: g.submit_answer(
                self._me(), data.get("assignment_id"), str(data.get("text", ""))))

        @sio.on("mark")
        def mark(data):
            self.run_action(lambda: g.mark(self._me(), data.get("answer_id"), data.get("mark")))

        @sio.on("undo")
        def undo(*_):
            self.run_action(lambda: g.undo_mark(self._me()))

        @sio.on("highlight")
        def highlight(data):
            self.run_action(lambda: g.choose_highlight(
                self._me(), data.get("answer_id"), bool(data.get("show"))))

        @sio.on("host")
        def host(data):
            self.run_action(lambda: self._host_action(data.get("action")))

        @sio.on("dev")
        def dev(data):
            self.run_action(lambda: self._dev_action(data.get("action"), data))

    # ---------------------------------------------------------------- host & dev

    def _check_host(self) -> None:
        sid = request.sid
        if self.tv_sids.get(sid):
            return  # the TV page opened on this PC
        pid = self.phone_sids.get(sid)
        if pid and self.game.players.get(pid) and self.game.players[pid].is_host:
            return
        raise GameError("Only the host can do that.")

    def _host_action(self, action: str) -> None:
        self._check_host()
        g = self.game
        if action == "start":
            g.start()
        elif action == "end":
            deadline = g.end_party()
            if deadline:
                start_grace_timer(self.socketio, g, deadline, self.broadcast)
        elif action == "highlights":
            g.show_highlights()
        elif action == "next":
            g.advance()
        elif action == "new_game":
            g.new_game()
        else:
            raise GameError("Unknown action.")

    def _dev_action(self, action: str, data: dict) -> None:
        if not (self.dev and self.tv_sids.get(request.sid)):
            raise GameError("Dev controls are off. Start with --dev.")
        g = self.game
        if action == "add_bots":
            self.bots.request(int(data.get("count", 1)))
            if g.host is None:
                raise GameError("Bots will join as soon as the host does.")
        elif action == "bots_now":
            self.bots.act_now()
        elif action == "skip_timer":
            g.finish_grace()
        elif action == "mark_all":
            mark_everything(g, self.rng)
        elif action == "reset":
            g.new_game()
        else:
            raise GameError("Unknown dev action.")
