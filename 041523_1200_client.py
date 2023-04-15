
import cv2
import socket
import struct
import pickle

client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_ip = '10.0.0.12'  # Replace with the server's IP address
port = 9999
client_socket.connect((server_ip, port))
print("[INFO] Connected to server")

data = b""
payload_size = struct.calcsize("L")

try:
    while True:
        # Receive the size of the pickled frame
        while len(data) < payload_size:
            packet = client_socket.recv(4096)
            if not packet:  # Check for empty packet (disconnection)
                raise Exception("Connection closed by server.")
            data += packet
        packed_message_size = data[:payload_size]
        data = data[payload_size:]
        message_size = struct.unpack("L", packed_message_size)[0]
        print(f"[INFO] Frame size: {message_size}")  # Debugging print statement

        # Receive the actual pickled frame
        while len(data) < message_size:
            data += client_socket.recv(4096)
        frame_data = data[:message_size]
        data = data[message_size:]

        # Deserialize and display frame
        frame = pickle.loads(frame_data)
        cv2.imshow("Video Frame", frame)
        print("[INFO] Received and displayed frame.")  # Debugging print statement

        if cv2.waitKey(1) == ord('q'):  # Press 'q' to exit
            break
finally:
    client_socket.close()
    cv2.destroyAllWindows()
