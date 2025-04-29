# Communication Network Final Project

## PerfectSocket

using reed-solomon encoding to encode and decode data.

let k be the number of original fragments, n be the total number of fragments.

i.e. if k = 4, n = 16, then there are 4 original fragments and 12 redundant fragments.

and reed-solomon decoding just need k fragments to decode the original data.

so the worst case is that n - k fragments are lost, and we can still decode the original data.

### sendto

1. input original data:

   ```python
   data = b"Hello, World!"
   ```

2. split into 4 fragments, if the length of data is not divisible by 4, pad with null bytes:

   ```python
   data = [b"Hell", b"o, W", b"orld", b"!\x00\x00\x00"]
   ```

3. reed-solomon encoding with k = 4, n = 16:

   ```python
   from zfec import Encoder

   encoder = Encoder(4, 16)
   encoded = encoder.encode(data)
   ```

   it will return 16 fragments, 4 of them are the original fragments, the rest are parity fragments.

   ```python
   encoded = [b'Hell', b'o, W', b'orld', b'!\x00\x00\x00', b'\x82\x91\xb4\xe5', b'\xf5\x10\xc0\xb3', b'eR%\x94', b'\x833\x8e\r',     b'\xf4VR\x1f', b'\x83\x9af\xc5', b'\xf6n\x9b\xe3', b',-\x19\x13', b'R\x16\xd1\x9d', b'ml\xc5\xec', b'\x91\xf60\xb2', b'g\xb0\xf8\xeb']
   ```

4. packet header:

   ```python
   import struct

   packets = []
   for batch_id, fragment in enumerate(encoded):
       header = struct.pack(">IBBBH", batch_id, idx, k, n, orig_len)
       packet = header + fragment
       packets.append(packet)
   ```

5. send packets:

   ```python
   import socket

   s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
   for packet in packets:
       s.sendto(packet, (DST_IP, DST_PORT))
   ```

### recvfrom

1. receive packets:

   ```python
   import socket

   s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
   packets = []
   while True:
       packet, addr = s.recvfrom(65535)
       packets.append(packet)
   ```

2. unpack header:

   ```python
   import struct

   batch_idxs = []
   encodeds = []
   for packet in packets:
       header = struct.unpack(">IBBBH", packet[:9])
       batch_id, idx, k, n, orig_len = header
       batch_idxs.append(batch_id)
       encodeds.append(packet[9:])
   ```

3. decode:

   ```python
   from zfec import Decoder

   decoder = Decoder(k, n)
   decoded = decoder.decode(encodeds, batch_idxs)
   ```

4. join fragments:

   ```python
   decoded = b''.join(decoded)
   ```

5. remove padding:

   ```python
   decoded = decoded[:orig_len]
   ```

6. return decoded data:

   ```python
   return decoded
   ```

## Experiments

### Text

```
client_text (with PerfectSocket sendto)
      |
      | UDP (encoded packets)
      v
    proxy
      |
      | UDP (lossy/delay encoded packets)
      v
server_text (with PerfectSocket recvfrom)
```

### Video

```
ffmpeg -re -i video.mp4 -f mpegts udp://127.0.0.1:12345
      |
      | UDP (normal packets)
      v
client_video (receive ffmpeg output from UDP port 12345 and send to UDP port 5405 with PerfectSocket)
      |
      | UDP (encoded packets)
      v
    proxy
      |
      | UDP (lossy/delay encoded packets)
      v
server_video (receive encoded packets from UDP port 5405 with PerfectSocket and send to UDP port 23456 with normal Socket)
      |
      | UDP (normal packets)
      v
ffplay -fflags nobuffer -flags low_delay -i udp://0.0.0.0:23456
```

## commands

### ffmpeg

```bash
ffmpeg -re -i video.mp4 -f mpegts udp://127.0.0.1:12345
```

```bash
ffplay -fflags nobuffer -flags low_delay -i udp://0.0.0.0:23456
```

### Docker

```bash
docker compose up
```

```bash
docker exec -it server bash
docker exec -it proxy bash
docker exec -it client bash
```
