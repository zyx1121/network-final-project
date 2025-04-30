import math
import socket
import struct
import time
import threading
import queue
import logging
from collections import deque
import random

from zfec import Decoder, Encoder


class PerfectSocket:
    """
    A UDP socket wrapper supporting FEC (Forward Error Correction) for reliable data transmission.
    """

    def __init__(
        self,
        bind_addr=None,
        max_queue_size=200,
        max_send_rate=None,
        on_send_error=None,
        on_queue_full=None,
        on_decode_error=None,
        send_retry=0,
        drop_if_full=False,
        processed_maxlen=10000,
        batch_timeout=10,
    ):
        """
        Initialize PerfectSocket.

        Args:
            bind_addr (tuple): (host, port) to bind, or None for no binding.
            max_queue_size (int): Max size of the send queue to avoid memory overflow.
            max_send_rate (float): Max send rate (batch/sec), None for unlimited.
            on_send_error (callable): Callback on send failure, args (exception, data, address).
            on_queue_full (callable): Callback when queue is full, args (data, address).
            on_decode_error (callable): Callback on decode failure, args (exception, batch_id).
            send_retry (int): Number of retries on send failure.
            drop_if_full (bool): If True, drop new data when queue is full; otherwise block.
            processed_maxlen (int): Max number of processed_batches to keep.
            batch_timeout (float): Timeout seconds for each batch.
        """
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        if bind_addr:
            self.sock.bind(bind_addr)
        self.batches = {}
        self._batch_timestamps = {}  # Record batch creation time
        self.processed_batches = deque(
            maxlen=processed_maxlen
        )  # Auto-recycle with deque
        self._processed_set = set()  # For fast lookup with deque

        # Send queue and thread
        self._send_queue = queue.Queue(maxsize=max_queue_size)
        self._max_send_rate = max_send_rate
        self._stop_event = threading.Event()
        self._send_thread = threading.Thread(target=self._send_worker, daemon=True)
        self._send_thread.start()

        self._closed = False  # Closed state flag

        # Error callbacks
        self._on_send_error = on_send_error
        self._on_queue_full = on_queue_full
        self._on_decode_error = on_decode_error
        self._send_retry = send_retry
        self._drop_if_full = drop_if_full

        # Statistics
        self._stat_send_batch = 0
        self._stat_send_drop = 0
        self._stat_send_fail = 0
        self._stat_queue_full = 0
        self._stat_recv_batch = 0
        self._stat_decode_fail = 0
        self._stat_send_total_delay = 0.0

        self._batch_timeout = batch_timeout

        self._batch_id_counter = 0
        self._batch_id_lock = threading.Lock()
        self._client_id = random.getrandbits(32)  # 32-bit unique identifier

    def __enter__(self):
        """
        Support for with statement.
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Automatically close socket when exiting with block.
        """
        self.close()

    def __del__(self):
        """
        Release resources when object is garbage collected.
        """
        self.close(wait_queue=False)

    def sendto(self, data: bytes, address, redundancy_ratio=2, mtu=1400, min_k=4):
        """
        Send data (asynchronously, actual sending is handled by background thread).

        Args:
            data (bytes): Data to send.
            address (tuple): Target (host, port).
            redundancy_ratio (int): Redundancy ratio, n = k * redundancy_ratio.
            mtu (int): Maximum packet size.
            min_k (int): Minimum number of fragments.
        """
        if self._closed:
            raise RuntimeError("PerfectSocket is closed, cannot sendto.")
        k = max(min_k, math.ceil(len(data) / mtu))
        n = k * redundancy_ratio
        try:
            if self._drop_if_full:
                self._send_queue.put_nowait((data, address, k, n, time.time()))
            else:
                self._send_queue.put((data, address, k, n, time.time()))
        except queue.Full:
            self._stat_queue_full += 1
            self._stat_send_drop += 1
            if self._on_queue_full:
                self._on_queue_full(data, address)
            else:
                logging.warning("PerfectSocket: send queue full, data dropped.")
            logging.debug(
                f"PerfectSocket: queue full, total dropped: {self._stat_send_drop}"
            )

    def _pack_header(self, batch_id, idx, k, n, orig_len):
        """
        Pack packet header.
        """
        return struct.pack(
            ">IIBBBH",
            self._client_id,
            batch_id,
            idx,
            k,
            n,
            orig_len,
        )

    def _send_fragment(self, packet, address, data, retry_limit):
        """
        Send a single fragment, retry on failure.
        """
        retry = 0
        while retry <= retry_limit:
            try:
                self.sock.sendto(packet, address)
                return True
            except OSError as e:
                retry += 1
                if retry > retry_limit:
                    self._stat_send_fail += 1
                    if self._on_send_error:
                        self._on_send_error(e, data, address)
                    else:
                        logging.error(f"PerfectSocket: sendto failed: {e}")
                    return False
                time.sleep(0.01)  # Wait before retry

    def _send_worker(self):
        """
        Background thread: fetch data from queue and actually send.
        """
        last_send_time = 0
        while not self._stop_event.is_set() or not self._send_queue.empty():
            try:
                data, address, k, n, enqueue_time = self._send_queue.get(timeout=0.1)
            except queue.Empty:
                continue
            batch_id = self._next_batch_id()

            block_size = math.ceil(len(data) / k)
            pad_len = block_size * k - len(data)
            if pad_len > 0:
                data += b"\0" * pad_len  # Pad the last block

            # Split data into blocks
            blocks = [data[i * block_size : (i + 1) * block_size] for i in range(k)]
            encoder = Encoder(k, n)
            fragments = encoder.encode(blocks)

            send_failed = False
            for idx, fragment in enumerate(fragments):
                header = self._pack_header(batch_id, idx, k, n, len(data) - pad_len)
                packet = header + fragment
                if not self._send_fragment(packet, address, data, self._send_retry):
                    send_failed = True
                    break

            if not send_failed:
                self._stat_send_batch += 1
                delay = time.time() - enqueue_time
                self._stat_send_total_delay += delay
                logging.debug(
                    f"PerfectSocket: sent batch_id={batch_id}, k={k}, n={n}, "
                    f"delay={delay:.4f}s, total_sent={self._stat_send_batch}"
                )
            else:
                self._stat_send_drop += 1
                logging.debug(
                    f"PerfectSocket: send batch_id={batch_id} failed, total_failed={self._stat_send_fail}, total_dropped={self._stat_send_drop}"
                )
            # Rate limiting
            if self._max_send_rate:
                interval = 1.0 / self._max_send_rate
                now = time.time()
                sleep_time = interval - (now - last_send_time)
                if sleep_time > 0:
                    time.sleep(sleep_time)
                last_send_time = time.time()

    def recvfrom(self, timeout=None):
        """
        Receive data (blocking until a complete batch is received).

        Args:
            timeout (float): Socket timeout in seconds, None for unlimited.

        Returns:
            (data_bytes, addr): Decoded data and source address.
        """
        if self._closed:
            raise RuntimeError("PerfectSocket is closed, cannot recvfrom.")
        if timeout is not None:
            self.sock.settimeout(timeout)
        while True:
            # --- Clean up expired batches ---
            now = time.time()
            expired = [
                key
                for key, t in self._batch_timestamps.items()
                if now - t > self._batch_timeout
            ]
            for key in expired:
                if key in self.batches:
                    del self.batches[key]
                del self._batch_timestamps[key]
                logging.debug(
                    f"PerfectSocket: batch {key} timeout, removed from memory."
                )

            try:
                packet, addr = self.sock.recvfrom(65535)
            except (OSError, socket.error):
                raise RuntimeError("PerfectSocket is closed, cannot recvfrom.")
            header = packet[:13]
            client_id, batch_id, idx, k, n, orig_len = struct.unpack(">IIBBBH", header)
            fragment = packet[13:]

            key = (client_id, batch_id)

            if key in self._processed_set:
                continue

            if key not in self.batches:
                self.batches[key] = {"k": k, "n": n, "fragments": {}}
                self._batch_timestamps[key] = time.time()

            batch = self.batches[key]
            batch["fragments"][idx] = fragment

            # Try to decode when k fragments are collected
            if len(batch["fragments"]) >= batch["k"]:
                fragment_ids = list(batch["fragments"].keys())
                fragment_datas = [batch["fragments"][i] for i in fragment_ids]
                try:
                    decoder = Decoder(batch["k"], batch["n"])
                    decoded_data = decoder.decode(fragment_datas, fragment_ids)
                    data_bytes = b"".join(decoded_data)[:orig_len]
                except Exception as e:
                    self._stat_decode_fail += 1
                    if self._on_decode_error:
                        self._on_decode_error(e, key)
                    else:
                        logging.error(
                            f"PerfectSocket: decode failed for batch {key}: {e}"
                        )
                    logging.debug(
                        f"PerfectSocket: decode failed, batch_id={key}, total_decode_fail={self._stat_decode_fail}"
                    )
                    # Mark as processed and clean up
                    self._processed_set.add(key)
                    self.processed_batches.append(key)
                    if key in self.batches:
                        del self.batches[key]
                    if key in self._batch_timestamps:
                        del self._batch_timestamps[key]
                    continue
                self._stat_recv_batch += 1
                logging.debug(
                    f"PerfectSocket: received batch_id={key}, k={batch['k']}, n={batch['n']}, total_recv={self._stat_recv_batch}"
                )
                # Mark as processed and clean up
                self._processed_set.add(key)
                self.processed_batches.append(key)
                if key in self.batches:
                    del self.batches[key]
                if key in self._batch_timestamps:
                    del self._batch_timestamps[key]
                # Keep processed_batches and _processed_set in sync
                while len(self.processed_batches) > self.processed_batches.maxlen:
                    old = self.processed_batches.popleft()
                    self._processed_set.discard(old)
                return data_bytes, addr

    def close(self, wait_queue=True, timeout=None):
        """
        Close the socket and release resources.

        Args:
            wait_queue (bool): If True, wait for queue to be empty before closing; if False, close immediately (drop unsent data).
            timeout (float): Maximum wait time in seconds, None for unlimited.
        """
        if self._closed:
            return
        self._closed = True
        self._stop_event.set()
        if wait_queue:
            start_time = time.time()
            while self._send_thread.is_alive():
                self._send_thread.join(timeout=0.1)
                if timeout is not None and (time.time() - start_time) > timeout:
                    break
        try:
            self.sock.close()
        except Exception:
            pass
        # Print statistics summary
        if logging.getLogger().isEnabledFor(logging.DEBUG):
            avg_delay = (
                self._stat_send_total_delay / self._stat_send_batch
                if self._stat_send_batch > 0
                else 0
            )
            logging.debug(
                f"PerfectSocket stats: sent={self._stat_send_batch}, "
                f"recv={self._stat_recv_batch}, dropped={self._stat_send_drop}, "
                f"queue_full={self._stat_queue_full}, send_fail={self._stat_send_fail}, "
                f"decode_fail={self._stat_decode_fail}, avg_send_delay={avg_delay:.4f}s"
            )

    def _next_batch_id(self):
        """
        Generate the next batch id (32-bit, wraps around).
        """
        with self._batch_id_lock:
            self._batch_id_counter += 1
            return self._batch_id_counter & 0xFFFFFFFF
