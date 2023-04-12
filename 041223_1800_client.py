
import struct
from enum import Enum, auto
import cv2
import socket
import struct
import threading
import queue
import keyboard
import time
import numpy as np

class OmniCamPacketType(Enum):
    CAM_NO_PACKET = 0
    CAM_START = auto()
    CAM_STOP = auto()
    CAM_IMAGE_AVAIL = auto()
    CAM_WRITE_CONFIG = auto()
    CAM_READ_CONFIG = auto()
    CAM_PAN = auto()
    NUM_CAM_PACKET_TYPE = auto()

# Example usage
print(OmniCamPacketType.CAM_START)  # Output: OmniCamPacketType.CAM_START
print(OmniCamPacketType.CAM_START.value)  # Output: 1 (the automatically assigned value)

BYTE_ORDER_FLAG = 0x12345678  # Example value for the byte_order flag

# Define a Python class that represents the OmniCamPacket structure
class OmniCamPacket:
    def __init__(self, type):
        self.byte_order = BYTE_ORDER_FLAG
        self.type = type
        self.firmware_rev = 1
        self.horz_pan = 0
        self.vert_pan = 0
        self.fps = 0
        self.size = 0

# Define the format string for struct.pack and struct.unpack
# Assuming int and uint are both 4 bytes (32 bits)
# Format: Iiiiiii (I = unsigned int, i = signed int)
format_str = 'Iiiiiii'

# Pack the OmniCamPacket structure into bytes
def pack_omni_cam_packet(packet):
    return struct.pack(format_str, packet.byte_order, packet.type, packet.firmware_rev,
                       packet.horz_pan, packet.vert_pan, packet.fps, packet.size)

# Unpack bytes into the OmniCamPacket structure
def unpack_omni_cam_packet(data):
    unpacked_data = struct.unpack(format_str, data)
    packet = OmniCamPacket(unpacked_data[1])
    packet.byte_order = unpacked_data[0]
    packet.firmware_rev = unpacked_data[2]
    packet.horz_pan = unpacked_data[3]
    packet.vert_pan = unpacked_data[4]
    packet.fps = unpacked_data[5]
    packet.size = unpacked_data[6]
    return packet

# Example usage
packet = OmniCamPacket(type=OmniCamPacketType.CAM_PAN.value)

packet_vid = OmniCamPacket(type=OmniCamPacketType.CAM_IMAGE_AVAIL.value)

packed_data = pack_omni_cam_packet(packet)
print("Packed data:", packed_data)

unpacked_packet = unpack_omni_cam_packet(packed_data)
print("Unpacked packet:", unpacked_packet.__dict__)


def get_command(command_queue):
    print("in: get_command()")
    global packet
    while True:
        # Get user input for servo control
        packet.type = OmniCamPacketType.CAM_PAN.value
        packet.size = struct.calcsize(format_str)
        if keyboard.is_pressed('left'):
            packet.horz_pan = 1
            packed_data = pack_omni_cam_packet(packet)
            command_queue.put(packed_data)
        elif keyboard.is_pressed('right'):
            packet.horz_pan = -1
            packed_data = pack_omni_cam_packet(packet)
            command_queue.put(packed_data)
        # Add additional cases for other arrow keys as needed

        # Sleep briefly to reduce CPU usage
        time.sleep(0.5)

def send_command(client_socket, command_queue):
    # Create a socket object
    command_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Connect to the server
    command_socket.connect(('192.168.2.36', 8486))

    while True:
        try:
            # Wait for a command to be available in the queue (timeout of 1 second)
            command = command_queue.get(timeout=0.5)

            try:
                # Send the command to the server
                command_socket.sendall(command)
            except Exception as send_error:
                print(f"Error sending command to server: {send_error}")

        except queue.Empty:
            # No command received within the timeout period
            pass
        time.sleep(0.1)



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

frame_counter = 0

# Record the start time
start_time = time.time()
delta_time = 0

while True:
    try:
        # Receive the size of the image data
        #payload_size = struct.calcsize('>L')
        #packed_msg_size = client_socket.recv(payload_size)
        #msg_size = struct.unpack('>L', packed_msg_size)[0]
        #print ("JPG SIZE: ", msg_size)

        expected_length = struct.calcsize(format_str)

        packet_vid_data = b''
        while len(packet_vid_data) < expected_length:
            chunk = client_socket.recv(expected_length - len(packet_vid_data))
            packet_vid_data += chunk

        if len(packet_vid_data) != expected_length:
            # Partial or no data received, handle accordingly
            print("Received partial or no data")
            break

        # Unpack the OmniCamPacket structure
        packet_vid = unpack_omni_cam_packet(packet_vid_data)

        # Check if the packet type is CAM_IMAGE_AVAIL
        if packet_vid.type == OmniCamPacketType.CAM_IMAGE_AVAIL.value:
            # Get the message size from the OmniCamPacket structure
            msg_size = packet_vid.size
        else:
            print("Image availabe packet not sent")
            break

        # Receive the image data itself
        image_data = b''
        while len(image_data) < msg_size:
            remaining_bytes = msg_size - len(image_data)
            try:
                image_data += client_socket.recv(min(65536, remaining_bytes))
            except socket.error as e:
                print(f"An error occured while receiving data: {e}")
                break

        # Decode the received image data
        frame = np.frombuffer(image_data, dtype=np.uint8)
        frame = cv2.imdecode(frame, cv2.IMREAD_COLOR)

        # Increment and display the frame counter on the video frame
        frame_counter += 1
        elapsed_time = time.time() - start_time
        cv2.putText(frame, f"Frame: {frame_counter}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 50), 2)
        cv2.putText(frame, f"Elapsed Time: {elapsed_time:.2f} s", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 50), 2)

        # Display the frame
        cv2.imshow('Received Frame', frame)

        delta_time = elapsed_time - delta_time
        if (delta_time > 1):
            print(f"blocked for {delta_time} seconds")
            print(f"total elapsed time is: {elapsed_time}")
        delta_time = elapsed_time

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    except Exception as e:
        print(f"An overall error occurred: {e}")
        break

# Close the connection
client_socket.close()
cv2.destroyAllWindows()


