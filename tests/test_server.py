"""The web layer, using Flask's and Socket.IO's built-in test clients (no browser needed)."""
import io

import pytest

from mindblower.game import Game
from mindblower.server import Server, sniff_image
from conftest import HOST_KEY

JPEG = b"\xff\xd8\xff\xe0" + b"0" * 200


@pytest.fixture
def server(questions, tmp_path):
    game = Game(questions, HOST_KEY)
    return Server(game, port=5000, uploads_dir=tmp_path, join_host="192.168.1.42")


def join(server, name, host_key=None, data=JPEG):
    client = server.app.test_client()
    form = {"name": name, "selfie": (io.BytesIO(data), "selfie.jpg")}
    if host_key:
        form["host_key"] = host_key
    return client.post("/api/join", data=form, content_type="multipart/form-data")


def phone(server, player_id=None):
    sock = server.socketio.test_client(server.app)
    sock.emit("hello", {"role": "phone", "player_id": player_id})
    return sock


def last(sock, event="view"):
    events = [e for e in sock.get_received() if e["name"] == event]
    return events[-1]["args"][0] if events else None


def test_pages_load(server):
    client = server.app.test_client()
    assert client.get("/").status_code == 200
    assert client.get("/tv").status_code == 200
    assert client.get("/dev").status_code == 404  # only with --dev


def test_join_needs_host_first_and_a_real_image(server, tmp_path):
    assert join(server, "Mia").status_code == 400
    assert join(server, "Sam", HOST_KEY, data=b"not an image").status_code == 400
    res = join(server, "Sam", HOST_KEY)
    assert res.status_code == 200 and res.get_json()["is_host"] is True
    assert len(list(tmp_path.iterdir())) == 1  # the selfie was saved
    assert join(server, "Mia").status_code == 200


def test_reconnecting_with_the_same_id_gets_your_view_back(server):
    pid = join(server, "Sam", HOST_KEY).get_json()["player_id"]
    view = last(phone(server, pid))
    assert view["screen"] == "lobby" and view["me"]["name"] == "Sam"
    assert view["me"]["is_host"] is True


def test_unknown_id_is_forgotten(server):
    sock = phone(server, "made-up-id")
    received = sock.get_received()
    assert any(e["name"] == "forget" for e in received)
    assert [e for e in received if e["name"] == "view"][-1]["args"][0]["screen"] == "join"


def test_only_the_host_can_start(server):
    host = phone(server, join(server, "Sam", HOST_KEY).get_json()["player_id"])
    mia = phone(server, join(server, "Mia").get_json()["player_id"])
    phone(server, join(server, "Leo").get_json()["player_id"])
    mia.emit("host", {"action": "start"})
    assert "host" in last(mia, "oops")["message"]
    host.emit("host", {"action": "start"})
    assert last(host)["screen"] == "categories"


def test_bad_input_gets_a_friendly_message(server):
    host = phone(server, join(server, "Sam", HOST_KEY).get_json()["player_id"])
    host.emit("pick", {"category": "small_talk"})  # still in the lobby
    assert last(host, "oops")["message"]
    host.emit("mark", {"answer_id": "nope", "mark": "correct"})
    assert last(host, "oops")["message"]


def test_tv_view_shows_qr_only_after_the_host_joins(server):
    tv = server.socketio.test_client(server.app)
    tv.emit("hello", {"role": "tv"})
    assert last(tv)["qr"] is None
    join(server, "Sam", HOST_KEY)
    view = last(tv)
    assert "<svg" in view["qr"]
    assert view["join_url"] == "http://192.168.1.42:5000/"


def test_sniff_image():
    assert sniff_image(JPEG) == "jpg"
    assert sniff_image(b"\x89PNG\r\n\x1a\n....") == "png"
    assert sniff_image(b"RIFF....WEBPVP8 ") == "webp"
    assert sniff_image(b"<svg>") is None
