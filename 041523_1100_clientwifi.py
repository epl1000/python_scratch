import cv2
import socket
import struct
import pickle

client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_ip = 'SERVER_IP'  # Replace with the server's IP address
port = 9999              # Port number for the server

client_socket.connect((server_ip, port))
print("[INFO] Connected to server")

data = b""
payload_size = struct.calcsize("L")

while True:
    while len(data) < payload_size:
        data += client_socket.recv(4096)
    packed_message_size = data[:payload_size]
    data = data[payload_size:]
    message_size = struct.unpack("L", packed_message_size)[0]

    while len(data) < message_size:
        data += client_socket.recv(4096)
    frame_data = data[:message_size]
    data = data[message_size:]

    # Deserialize and display frame
    frame = pickle.loads(frame_data)
    cv2.imshow("Video Frame", frame)

    if cv2.waitKey(1) == ord('q'):  # Press 'q' to exit
        break

client_socket.close()
cv2.destroyAllWindows()

