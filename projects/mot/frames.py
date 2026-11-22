"""Portable frame validation shared by render and encode commands."""
import struct


def valid_png(path, width, height):
    try:
        with path.open('rb') as handle:
            header = handle.read(24)
            handle.seek(-8, 2)
            trailer = handle.read(8)
        return (header[:8] == b'\x89PNG\r\n\x1a\n'
                and struct.unpack('>II', header[16:24]) == (width, height)
                and trailer == b'IEND\xaeB`\x82')
    except (OSError, struct.error):
        return False
