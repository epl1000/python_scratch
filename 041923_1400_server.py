import cv2
import socket
import struct
import pickle
import threading
import time
import pigpio
import struct
from enum import Enum, auto

class OmniCamPacketType(Enum):
    CAM_NO_PACKET = 0
    CAM_START = auto()
    CAM_STOP = auto()
    CAM_IMAGE_AVAIL = auto()
    CAM_WRITE_CONFIG = auto()
    CAM_READ_CONFIG = auto()
    CAM_PAN = auto()
    NUM_CAM_PACKET_TYPE = auto()


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
packet = OmniCamPacket(type=2)
packet.horz_pan = 0
packet.vert_pan = 0
packet.fps = 15
packet.size = 64

video_streaming = False
video_streaming_event = threading.Event()
receive_thread_lock = threading.Lock()
receive_command_exit_event = threading.Event()



#----SERVO CODE
servo_pin = 18
servo_pin_tilt = 12

print("pigpio object about to initiate")
pi = pigpio.pi()
print("pigpio object created")

neutral_pw = 1500
curr_pw = neutral_pw
curr_pw_tilt = neutral_pw

#center servo on boot
#time.sleep(1)
print(f"At servo pos 1")
pi.set_servo_pulsewidth(servo_pin, 1500)
print(f"At servo pos 2")
pi.set_servo_pulsewidth(servo_pin_tilt, 1500)
print(f"At servo pos 3")

def ensure_valid_pw(curr_pw):
    MIN_PW = 800
    MAX_PW = 2200
    
    if curr_pw == 0:
        return curr_pw
    elif curr_pw < MIN_PW:
        return MIN_PW
    elif curr_pw > MAX_PW:
        return MAX_PW
    else:
        return curr_pw
     

def right():
    global curr_pw
    curr_pw = curr_pw + 10
    curr_pw = ensure_valid_pw(curr_pw)
    pi.set_servo_pulsewidth(servo_pin, curr_pw)

def left():
    global curr_pw
    curr_pw = curr_pw - 10
    curr_pw = ensure_valid_pw(curr_pw)
    pi.set_servo_pulsewidth(servo_pin, curr_pw)
    
def up():
    global curr_pw_tilt
    curr_pw_tilt = curr_pw_tilt + 10
    curr_pw_tilt = ensure_valid_pw(curr_pw_tilt)
    pi.set_servo_pulsewidth(servo_pin_tilt, curr_pw_tilt)

def down():
    global curr_pw_tilt
    curr_pw_tilt = curr_pw_tilt - 10
    curr_pw_tilt = ensure_valid_pw(curr_pw_tilt)
    pi.set_servo_pulsewidth(servo_pin_tilt, curr_pw_tilt)

def process_command(unpacked_packet):
    # Implement the logic to control servos based on the received command
    if unpacked_packet.type == OmniCamPacketType.CAM_PAN.value:    
        if unpacked_packet.horz_pan == -1:
            left()
        elif unpacked_packet.horz_pan == 1:
            right()
        elif unpacked_packet.vert_pan == 1:
            up()
        elif unpacked_packet.vert_pan == -1:
            down()
    
    
def receive_command_wrapper(conn_com):
    try:
        receive_command(conn_com)
    finally:
        receive_thread_lock.release()
    
def receive_command(conn_com): 
    #global video_streaming
    
    # Determine the expected length of an OmniCamPacket
    expected_length = struct.calcsize(format_str)
    
    while True:
        #time.sleep(1)
        try:
            # Receive and process the command from the client
            # Accumulate received data until the full packet is received
            packet = b''
            while len(packet) < expected_length:
                chunk = conn_com.recv(expected_length - len(packet))
                if not chunk:
                    return  # Client disconnected
                packet += chunk
            
            if len(packet) != expected_length:
                # Partial or no data received, handle accordingly
                return
            
            unpacked_packet = unpack_omni_cam_packet(packet)
            if unpacked_packet.type == OmniCamPacketType.CAM_START.value:
                #video_streaming = True
                video_streaming_event.set()
                print("got video streaming true command")
            elif unpacked_packet.type == OmniCamPacketType.CAM_STOP.value:
                #video_streaming = False
                video_streaming_event.clear()
                print("got video streaming false command")
            else:
                process_command(unpacked_packet)
        except Exception as e:
            print(f"Error Receiving Commands: {e}")
            break
    #print("receive command thread ended")
    #conn_com.close()
    
def main():
    # Create a socket object for command receiving
    server_socket_com = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket_com.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket_com.bind(('0.0.0.0', 8486))
    server_socket_com.listen(1)

    # Create a socket object for video streaming
    server_socket_vid = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket_vid.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket_vid.bind(('0.0.0.0', 8485))
    server_socket_vid.listen(1)

    # Open the camera (use 0 for the default camera)
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS, 15)
    
    #global video_streaming

    while True:
        try:
            # Accept a connection for command receiving
            conn_com, addr1 = server_socket_com.accept()

            # Start thread for receiving commands
            receive_thread_lock.acquire()
            receive_command_exit_event.clear()
            receive_thread = threading.Thread(target=receive_command_wrapper, args=(conn_com,))
            receive_thread.daemon = True
            receive_thread.start()

            # Accept a connection for video streaming
            conn, addr = server_socket_vid.accept()
            #ret, frame = cap.read()
            #result, frame = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])

            # Video streaming loop
            while True:
               # send CAM_IMAGE_AVAIL packet type with image size
                ret, frame = cap.read()
                
                if video_streaming_event.is_set():
                    result, frame = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                    packet.type = OmniCamPacketType.CAM_IMAGE_AVAIL.value
                    packet.size = len(frame)
                    packed_data = pack_omni_cam_packet(packet)
                    conn.sendall(packed_data)
                    conn.sendall(frame)
                #else:
                    #packet.type = OmniCamPacketType.CAM_NO_PACKET.value
                    #packed_data = pack_omni_cam_packet(packet)
                    #conn.sendall(packed_data)
                    #time.sleep(0.1)
        except socket.error as e:
            # Handle socket error
            print(f"An error occurred while connecting to client: {e}")
            #video_streaming = True
            # Clean up the connections and continue waiting for next client
        except Exception as e:
            # Handle any other unexpected exceptions
            print(f"An unexpected error occurred: {e}")
            #video_streaming = True
        finally:
            # Signalthe receive_command thread to exit and wait for it to finish
            receive_command_exit_event.set()
            receive_thread.join()
            # Clean up connections
            conn_com.close()
            conn.close()

    # Release the camera and close the server sockets
    cap.release()
    server_socket_com.close()
    server_socket_vid.close()

if __name__ == "__main__":
    main() 

