import cv2
import socket
import struct
import pickle
import threading
import queue
import keyboard
import time


def get_command(command_queue):
    print("in: get_command()")
    while True:
        # Get user input for servo control
        if keyboard.is_pressed('left'):
            print("left")
            command_queue.put('left')
        elif keyboard.is_pressed('right'):
            command_queue.put('right')
        # Add additional cases for other arrow keys as needed

        # Sleep briefly to reduce CPU usage
        time.sleep(0.1)

def send_command(client_socket, command_queue):
    while True:
        try:
            # Wait for a command to be available in the queue (timeout of 1 second)
            command = command_queue.get(timeout=1)
            # Send the command to the server
            client_socket.sendall(command.encode())
        except queue.Empty:
            # No command received within the timeout period
            pass


# Create a socket object
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Connect to the server
client_socket.connect(('192.168.2.36', 8485))

# Create a queue to communicate between threads
command_queue = queue.Queue()

# Start a thread to handle user input
input_thread = threading.Thread(target=get_command, args=(command_queue,))
input_thread.daemon = True
input_thread.start()

# Start a thread to send commands to the server
send_thread = threading.Thread(target=send_command, args=(client_socket, command_queue,))
send_thread.daemon = True
send_thread.start()

# Receive data from the server
data = b''
payload_size = struct.calcsize(">L")

while True:
    # Retrieve the size of the data
    while len(data) < payload_size:
        data += client_socket.recv(4096)
    packed_msg_size = data[:payload_size]
    data = data[payload_size:]
    msg_size = struct.unpack(">L", packed_msg_size)[0]

    # Retrieve the data
    while len(data) < msg_size:
        data += client_socket.recv(4096)
    frame_data = data[:msg_size]
    data = data[msg_size:]

    # Deserialize the data and decode the JPEG image
    frame = pickle.loads(frame_data)
    frame = cv2.imdecode(frame, cv2.IMREAD_COLOR)

    # Display the frame
    cv2.imshow('Video', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Close the connection
client_socket.close()
cv2.destroyAllWindows()



