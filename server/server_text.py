import time

from psocket import PerfectSocket

HOST_IP = "0.0.0.0"
HOST_PORT = 5405


def main():
    with PerfectSocket((HOST_IP, HOST_PORT)) as ps:
        sent_times = []
        received_times = []

        for _ in range(1001):
            data, addr = ps.recvfrom()
            received_time = time.time()
            received_times.append(received_time)
            data_str = data.decode("utf-8")
            print(data_str, "received at", received_time)
            sent_time = data_str.split(" ")[-1]
            sent_times.append(float(sent_time))

        print("--------------------------------")
        print("first sent at", sent_times[0])
        print("last received at", received_times[-1])
        print("completed in", received_times[-1] - sent_times[0])


if __name__ == "__main__":
    main()
