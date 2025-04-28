import math
import socket
import struct
import time

from zfec import Decoder, Encoder


class PerfectSocket:
    def __init__(self, bind_addr=None):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        if bind_addr:
            self.sock.bind(bind_addr)
        self.batches = {}
        self.processed_batches = set()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def sendto(self, data: bytes, address, k: int = 4):
        """
        Send data with erasure coding to the given address.
        data: bytes to send (one batch)
        address: (ip, port)
        k: number of data fragments (default 4)
        """
        n = 4 * k
        batch_id = int(time.time() * 1000) & 0xFFFFFFFF

        block_size = math.ceil(len(data) / k)
        pad_len = block_size * k - len(data)
        if pad_len > 0:
            data += b"\0" * pad_len

        blocks = [data[i * block_size : (i + 1) * block_size] for i in range(k)]

        encoder = Encoder(k, n)
        fragments = encoder.encode(blocks)

        for idx, fragment in enumerate(fragments):
            # +----------+--------+--------+--------+----------+
            # | batch_id | id     | k      | n      | data_len |
            # +----------+--------+--------+--------+----------+
            # | 4 bytes  | 1 byte | 1 byte | 1 byte | 4 bytes  |
            # +----------+--------+--------+--------+----------+
            header = struct.pack(">IBBBH", batch_id, idx, k, n, len(data) - pad_len)
            packet = header + fragment
            self.sock.sendto(packet, address)

    def recvfrom(self, timeout=None):
        """
        Receive and decode one complete batch.
        Returns: (data: bytes, addr)
        """
        if timeout is not None:
            self.sock.settimeout(timeout)
        while True:
            packet, addr = self.sock.recvfrom(65535)
            header = packet[:9]
            batch_id, idx, k, n, orig_len = struct.unpack(">IBBBH", header)
            fragment = packet[9:]

            if batch_id in self.processed_batches:
                continue

            if batch_id not in self.batches:
                self.batches[batch_id] = {"k": k, "n": n, "fragments": {}}

            batch = self.batches[batch_id]
            batch["fragments"][idx] = fragment

            if len(batch["fragments"]) >= batch["k"]:
                fragment_ids = list(batch["fragments"].keys())
                fragment_datas = [batch["fragments"][i] for i in fragment_ids]
                decoder = Decoder(batch["k"], batch["n"])
                decoded_data = decoder.decode(fragment_datas, fragment_ids)
                data_bytes = b"".join(decoded_data)[:orig_len]
                self.processed_batches.add(batch_id)
                del self.batches[batch_id]
                return data_bytes, addr

    def close(self):
        self.sock.close()
