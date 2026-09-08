"""Genera los iconos PNG de Morfeo sin dependencias.

No forma parte del build: los PNG están versionados y esto solo hace falta si cambia
el icono. Se escribió a mano en vez de tirar de Pillow para que regenerar los iconos
no exija montar un entorno de Python con dependencias.

    python scripts/make-icons.py public

iOS no acepta SVG en `apple-touch-icon`, de ahí que haya PNG y no solo el favicon.
"""
import struct
import sys
import zlib

BG = (0x17, 0x15, 0x1F)
MOON = (0x8B, 0x7B, 0xFF)
SS = 4  # supermuestreo para suavizar el borde de la luna


def png_bytes(width: int, height: int, rows: list[bytes]) -> bytes:
    raw = b"".join(b"\x00" + row for row in rows)

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)  # 8 bits, RGB
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )


def render(size: int, moon_scale: float) -> bytes:
    """Luna creciente centrada sobre fondo a sangre.

    `moon_scale` deja margen: los iconos maskable de Android y el recorte de iOS
    se comen los bordes, así que el dibujo se queda dentro del 60% central.
    """
    cx = cy = size / 2
    radius = size * moon_scale / 2
    # Círculo que muerde al principal por arriba a la derecha.
    bx, by, br = cx + radius * 0.42, cy - radius * 0.30, radius * 0.90

    rows = []
    for y in range(size):
        row = bytearray()
        for x in range(size):
            covered = 0
            for sy in range(SS):
                py = y + (sy + 0.5) / SS
                for sx in range(SS):
                    px = x + (sx + 0.5) / SS
                    in_disc = (px - cx) ** 2 + (py - cy) ** 2 <= radius**2
                    in_bite = (px - bx) ** 2 + (py - by) ** 2 <= br**2
                    if in_disc and not in_bite:
                        covered += 1
            alpha = covered / (SS * SS)
            row += bytes(round(BG[i] + (MOON[i] - BG[i]) * alpha) for i in range(3))
        rows.append(bytes(row))
    return png_bytes(size, size, rows)


if __name__ == "__main__":
    out = sys.argv[1].rstrip("/")
    for size, scale, name in (
        (180, 0.62, "apple-touch-icon.png"),  # iOS redondea él mismo; va a sangre
        (192, 0.60, "icon-192.png"),
        (512, 0.60, "icon-512.png"),
    ):
        path = f"{out}/{name}"
        with open(path, "wb") as fh:
            fh.write(render(size, scale))
        print(f"{path}  {size}x{size}")
