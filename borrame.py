import argparse
import socket
import struct
import threading
import time

BROADCAST_IP = '255.255.255.255'
PORT = 5005
GRACE_MS = 50  # You can set to 10, 20, 50, etc.
LATENCY_SMOOTHING_ALPHA = 0.1  # Smaller is smoother

def get_millis():
    return int(time.time() * 1000)

def master():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    start_time = get_millis()

    while True:
        now = get_millis()
        elapsed = now - start_time
        send_timestamp = now
        packet = struct.pack('!QQ', elapsed, send_timestamp)
        sock.sendto(packet, (BROADCAST_IP, PORT))
        print(f"[MASTER] Elapsed: {elapsed / 1000:.3f}s")
        time.sleep(1)

def follower():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('', PORT))
    sock.settimeout(2.0)

    start_time = get_millis()
    drift_correction = 0
    initialized = False
    lock = threading.Lock()

    def listener():
        nonlocal drift_correction, initialized, start_time
        smoothed_latency = 0
        alpha = LATENCY_SMOOTHING_ALPHA

        while True:
            try:
                t_recv = get_millis()
                data, _ = sock.recvfrom(1024)
                t_now = get_millis()

                # Unpack: elapsed_time, send_timestamp
                elapsed_master, t_sent_master = struct.unpack('!QQ', data)

                # Estimate raw one-way latency
                sample_latency = (t_now - t_sent_master) // 2

                if not initialized:
                    smoothed_latency = sample_latency
                    corrected_elapsed = elapsed_master + smoothed_latency
                    drift_correction = corrected_elapsed - (t_now - start_time)
                    initialized = True
                    print(f"[FOLLOWER] Initial sync: drift_correction = {drift_correction} ms")
                    continue

                # EMA smoothing
                smoothed_latency = int(alpha * sample_latency + (1 - alpha) * smoothed_latency)

                corrected_elapsed = elapsed_master + smoothed_latency
                local_elapsed = t_now - start_time + drift_correction
                drift = corrected_elapsed - local_elapsed

                if abs(drift) > GRACE_MS:
                    with lock:
                        drift_correction += drift
                    print(f"[FOLLOWER] Adjusted by {drift} ms (smoothed latency = {smoothed_latency} ms)")

            except socket.timeout:
                pass
                #print("[FOLLOWER] No signal from master (timeout)")

    threading.Thread(target=listener, daemon=True).start()

    while True:
        now = get_millis()
        with lock:
            local_elapsed = now - start_time + drift_correction
        print(f"[FOLLOWER] Elapsed: {local_elapsed / 1000:.3f}s")
        time.sleep(1)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['master', 'follower'], required=True)
    args = parser.parse_args()

    if args.mode == 'master':
        master()
    elif args.mode == 'follower':
        follower()

if __name__ == '__main__':
    main()
