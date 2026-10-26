"""Local IP address and QR codes (SVG for the TV, text for the PyCharm console)."""
from __future__ import annotations

import io
import socket

import qrcode
import qrcode.image.svg


def local_ip() -> str:
    """The PC's address on the Wi-Fi, e.g. 192.168.1.42.

    Connecting a UDP socket sends no traffic; it just makes the OS pick the
    network interface it would use, which tells us our own address.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        try:
            s.connect(("10.255.255.255", 1))
            return s.getsockname()[0]
        except OSError:
            return "127.0.0.1"


def qr_svg(url: str) -> str:
    """An SVG QR code that scales to fill its box."""
    img = qrcode.make(url, image_factory=qrcode.image.svg.SvgPathImage, border=1)
    svg = img.to_string(encoding="unicode")
    # Drop the fixed size so CSS can size it.
    return svg.replace('width="', 'data-w="', 1).replace('height="', 'data-h="', 1)


def qr_text(url: str) -> str:
    """A QR code drawn with block characters, for printing in the console."""
    qr = qrcode.QRCode(border=1)
    qr.add_data(url)
    out = io.StringIO()
    qr.print_ascii(out=out, invert=True)
    return out.getvalue()
