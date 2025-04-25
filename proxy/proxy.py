import random
import socket
import threading
import time

DST_IP = "192.168.2.3"
DST_PORT = 5405

HOST_IP = "192.168.2.100"
HOST_PORT = 5405

LOSS_RATE = 0.1
DELAY_RATE = 0.1
DELAY_TIME = 1


def main():
    c = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    c.bind((HOST_IP, HOST_PORT))

    def delay_packet(data):
        time.sleep(DELAY_TIME)
        c.sendto(data, (DST_IP, DST_PORT))
        print("delay", data)

    while True:
        data, addr = c.recvfrom(65535)

        if random.random() < LOSS_RATE:
            print("loss", data)
            continue
        elif random.random() < DELAY_RATE:
            thread_ = threading.Thread(target=delay_packet, args=(data,))
            thread_.start()
            continue

        c.sendto(data, (DST_IP, DST_PORT))
        print("forward", data)


if __name__ == "__main__":
    main()
