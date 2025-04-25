import socket
import struct
import time

from zfec import Decoder

HOST_IP = "192.168.2.3"
HOST_PORT = 5405


def unpack_packet(packet):
    """
    +----------+--------+--------+--------+----------+
    | batch_id | id     | k      | n      | data     |
    +----------+--------+--------+--------+----------+
    | 4 bytes  | 1 byte | 1 byte | 1 byte | variable |
    +----------+--------+--------+--------+----------+
    """
    header = packet[:7]
    batch_id, id, k, n = struct.unpack(">IBBB", header)
    data = packet[7:]
    return batch_id, id, k, n, data


def main():
    c = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    c.bind((HOST_IP, HOST_PORT))

    batches = {}
    processed_batches = set()
    sent_times = list()
    received_times = list()

    while True:
        if len(processed_batches) >= 1000:
            break

        packet, _ = c.recvfrom(65535)
        batch_id, id, k, n, data = unpack_packet(packet)

        if batch_id in processed_batches:
            continue

        if batch_id not in batches:
            batches[batch_id] = {"k": k, "n": n, "fragments": {}}

        batch = batches[batch_id]
        batch["fragments"][id] = data

        if len(batch["fragments"]) >= batch["k"]:
            fragment_ids = list(batch["fragments"].keys())
            fragment_datas = [batch["fragments"][i] for i in fragment_ids]
            decoder = Decoder(batch["k"], batch["n"])
            decoded_data = decoder.decode(fragment_datas, fragment_ids)

            data_bytes = b"".join(decoded_data)
            data_str = data_bytes.decode("utf-8")

            received_time = time.time()
            received_times.append(received_time)

            print(data_str, "received at", received_time)

            sent_time = data_str.split(" ")[-1]
            sent_times.append(float(sent_time))

            processed_batches.add(batch_id)
            del batches[batch_id]

    print("first sent at", sent_times[0])
    print("last received at", received_times[-1])
    print("completed in", received_times[-1] - sent_times[0])


if __name__ == "__main__":
    main()
