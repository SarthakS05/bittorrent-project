import hashlib
import random
import socket
import struct
import urllib.parse

import bencodepy
import requests


def load_torrent(path):
    with open(path, "rb") as file:
        metadata = bencodepy.decode(file.read())

    info = metadata[b"info"]
    info_hash = hashlib.sha1(bencodepy.encode(info)).digest()
    announce = metadata[b"announce"].decode()
    file_length = info.get(b"length", 0)
    file_name = info.get(b"name", b"unknown").decode()

    return {
        "announce": announce,
        "info_hash": info_hash,
        "file_length": file_length,
        "file_name": file_name,
    }


def tracker_request(metadata):
    peer_id = b"-PC0001-" + bytes(random.randint(0, 255) for _ in range(12))
    port = 6881
    params = {
        "info_hash": metadata["info_hash"],
        "peer_id": peer_id,
        "port": port,
        "uploaded": 0,
        "downloaded": 0,
        "left": metadata["file_length"],
        "compact": 1,
    }
    url = metadata["announce"] + "?" + urllib.parse.urlencode(params, doseq=True)
    response = requests.get(url, timeout=10)
    tracker_data = bencodepy.decode(response.content)
    return tracker_data, peer_id


def parse_peers(tracker_data):
    peers_binary = tracker_data[b"peers"]
    peers = []
    for index in range(0, len(peers_binary), 6):
        ip = ".".join(str(byte) for byte in peers_binary[index:index + 4])
        port = struct.unpack(">H", peers_binary[index + 4:index + 6])[0]
        peers.append((ip, port))
    return peers


def handshake(peer_ip, peer_port, info_hash, peer_id):
    sock = socket.socket()
    sock.settimeout(3)
    try:
        sock.connect((peer_ip, peer_port))
    except OSError:
        return False

    pstr = b"BitTorrent protocol"
    message = struct.pack("!B", len(pstr)) + pstr + (b"\x00" * 8) + info_hash + peer_id
    sock.send(message)
    response = sock.recv(68)
    sock.close()
    return len(response) >= 68


def main():
    torrent_path = "example.torrent"
    metadata = load_torrent(torrent_path)
    tracker_data, peer_id = tracker_request(metadata)
    peers = parse_peers(tracker_data)

    for ip, port in peers[:5]:
        if handshake(ip, port, metadata["info_hash"], peer_id):
            print(f"Handshake OK with {ip}:{port}")


if __name__ == "__main__":
    main()
