import argparse
import socket
import struct
import time

from zfec import Decoder, Encoder

DST_IP = "192.168.2.100"
DST_PORT = 5405


def pack_packet(batch_id, id, k, n, data):
    """
    +----------+--------+--------+--------+----------+
    | batch_id | id     | k      | n      | data     |
    +----------+--------+--------+--------+----------+
    | 4 bytes  | 1 byte | 1 byte | 1 byte | variable |
    +----------+--------+--------+--------+----------+
    """
    header = struct.pack(">IBBB", batch_id, id, k, n)
    return header + data


def send_packet(s, data):
    data = data.encode("utf-8")

    k = len(data)
    n = 2 * k

    batch_id = int(time.time() * 1000) & 0xFFFFFFFF  # 4 bytes

    block_size = len(data) // k
    blocks = [data[i * block_size : (i + 1) * block_size] for i in range(k)]

    encoder = Encoder(k, n)
    fragments = encoder.encode(blocks)

    for idx, fragment in enumerate(fragments):
        packet = pack_packet(batch_id, idx, k, n, fragment)
        s.sendto(packet, (DST_IP, DST_PORT))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", type=float, default=0.001)
    args = parser.parse_args()

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    for i in range(1, 1001):
        send_packet(s, f"packet {i} sent at {time.time()}")
        time.sleep(args.d)


if __name__ == "__main__":
    main()
