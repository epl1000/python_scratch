
import cv2
import socket
import struct
import pickle
import threading
import time
import pigpio
import struct
from enum import Enum, auto

start_time = time.time()

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
    def __init__(self, type = OmniCamPacketType.CAM_NO_PACKET.value):
        self.byte_order = BYTE_ORDER_FLAG
        self.type = type
        self.firmware_rev = 1
        self.horz_pan = 0
        self.vert_pan = 0
        self.fps = 15
        self.jpg_qual = 80
        self.size = 0

# Define the format string for struct.pack and struct.unpack
# Assuming int and uint are both 4 bytes (32 bits)
# Format: Iiiiiii (I = unsigned int, i = signed int)
format_str = 'Iiiiiiii'

# Pack the OmniCamPacket structure into bytes
def pack_omni_cam_packet(packet):
    return struct.pack(format_str, packet.byte_order, packet.type, packet.firmware_rev,
                       packet.horz_pan, packet.vert_pan, packet.fps, packet.jpg_qual, packet.size)

# Unpack bytes into the OmniCamPacket structure
def unpack_omni_cam_packet(data):
    unpacked_data = struct.unpack(format_str, data)
    packet = OmniCamPacket(unpacked_data[1])
    packet.byte_order = unpacked_data[0]
    packet.firmware_rev = unpacked_data[2]
    packet.horz_pan = unpacked_data[3]
    packet.vert_pan = unpacked_data[4]
    packet.fps = unpacked_data[5]
    packet.jpg_qual = unpacked_data[6]
    packet.size = unpacked_data[7]
    return packet

vid_event = threading.Event()

#----SERVO CODE
servo_pin_pan = 18
servo_pin_tilt = 12

pi = pigpio.pi()

neutral_pw = 1500

fps = 15
jpg_qual = 80

#center servo on boot
pi.set_servo_pulsewidth(servo_pin_pan, 1500)
pi.set_servo_pulsewidth(servo_pin_tilt, 1000)

def ensure_valid_pw(curr_pw):
    MIN_PW = 800
    MAX_PW = 2200
    
    if curr_pw == 0:
        return 0;
    elif curr_pw < MIN_PW:
        return MIN_PW
    elif curr_pw > MAX_PW:
        return MAX_PW
    else:
        return curr_pw
     
    
def pan(packet):
    print("pan");   
    if packet.horz_pan != 0:
        curr_pw_pan = ensure_valid_pw(packet.horz_pan)
        pi.set_servo_pulsewidth(servo_pin_pan, curr_pw_pan)
        
    if packet.vert_pan != 0:
        curr_pw_tilt = ensure_valid_pw(packet.vert_pan)
        pi.set_servo_pulsewidth(servo_pin_tilt, curr_pw_tilt)
   
   
def process_command(conn_com, pack):
    global vid_event
    global fps
    global jpg_qual
    
    # Implement the logic to control servos based on the received command
    if pack.type == OmniCamPacketType.CAM_START.value:
        if pack.fps >= 1 and pack.fps <= 30:
            fps = pack.fps
        if pack.jpg_qual >= 10 and pack.jpg_qual <= 100:
            jpg_qual = pack.jpg_qual
        
        vid_event.set()
        print("    got video streaming true command")
    elif pack.type == OmniCamPacketType.CAM_STOP.value:
        vid_event.clear()
        print("    got video streaming false command")
    elif pack.type == OmniCamPacketType.CAM_PAN.value:
        pan(pack)
    elif pack.type == OmniCamPacketType.CAM_READ_CONFIG.value:
         print("****** read config")
         pack.horz_pan = pi.get_servo_pulsewidth(servo_pin_pan)
         pack.vert_pan = pi.get_servo_pulsewidth(servo_pin_tilt)
         packed_data = pack_omni_cam_packet(pack)
         conn_com.sendall(packed_data)

    else:
        print("Some other kind of command sent")

    
def receive_command(conn_com): 
    global start_time
    
    print("  recv command start")
    # Determine the expected length of an OmniCamPacket
    expected_length = struct.calcsize(format_str)
    cmd_num = 0
    while True:
        try:
            # Receive and process the command from the client
            # Accumulate received data until the full packet is received
            packet = b''

            try:
                packet = conn_com.recv(expected_length, socket.MSG_WAITALL)
                print(f"    expected length: {expected_length}")
            except Exception as e:
                print(f"    Error Receiving Command Packet: {e}")
                break
            
            dt = time.time() - start_time
            
            print(f"    got command {cmd_num} {dt}")
            cmd_num = cmd_num + 1
            
            if len(packet) != expected_length:
                # Partial or no data received, handle accordingly
                break
            
            unpacked_packet = unpack_omni_cam_packet(packet)
            process_command(conn_com, unpacked_packet)
        except Exception as e:
            print(f"    Error Receiving Commands: {e}")
            break
    print("  receive command ended")

def command_thread():
   # Create a socket object for command receiving
    server_socket_com = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket_com.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket_com.bind(('0.0.0.0', 56000))
    server_socket_com.listen(1)
    
    print("command thread")
    
    while True:
        
        print("  outer command loop")
        
        try:    
              # Accept a connection for command receiving
            conn_com, addr1 = server_socket_com.accept()
            
            receive_command(conn_com)
            
            conn_com.shutdown(socket.SHUT_RDWR)
            conn_com.close()
  
        except socket.error as e:
            # Handle socket error
            print(f"  An error occurred while accept command: {e}")
            #video_streaming = True
            # Clean up the connections and continue waiting for next client
        except Exception as e:
            # Handle any other unexpected exceptions
            print(f"  An unexpected error occurred in accept cmd: {e}")
            #video_streaming = True



def send_frames(conn, cap):
    global vid_event
    global fps
    global jpg_qual
    
    print("  send frames begin")
    print(f"  fps = {fps} jpg_qual = {jpg_qual}")
    if fps < 1 or fps > 30:
        fps = 15;
        
    delay = 1/fps
    
    if jpg_qual < 10 or jpg_qual > 100:
        jpg_qual = 80
    
    print(f"delay {delay}");

    packet = OmniCamPacket()

    frame_count = 0
    # Video streaming loop
    while True:
        try:
            print("     wait for event set")
            vid_event.wait()
            #print("    get frame")
            # send CAM_IMAGE_AVAIL packet type with image size
            ret, frame = cap.read()
            #print(f"    end frame {frame_count}")
            frame_count = frame_count+1
                
            #print("    send frame")
            result, frame = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, jpg_qual])
            packet.type = OmniCamPacketType.CAM_IMAGE_AVAIL.value
            packet.size = len(frame)
            packed_data = pack_omni_cam_packet(packet)
            conn.sendall(packed_data)
            conn.sendall(frame)

            time.sleep(delay)

        except socket.error as e:
            # Handle socket error
            print(f"  An error occurred send video: {e}")
            break
        except Exception as e:
            # Handle any other unexpected exceptions
            print(f"  An unexpected error in send frame: {e}")
            break

    
def main():
    # Start thread for receiving commands
    #receive_thread_lock.acquire()
    receive_thread = threading.Thread(target=command_thread)
    receive_thread.daemon = True
    receive_thread.start()

 
    # Create a socket object for video streaming
    server_socket_vid = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket_vid.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket_vid.bind(('0.0.0.0', 56100))
    server_socket_vid.listen(1)

    
    global video_streaming

    #  Create camera capture object
    cap = cv2.VideoCapture(0)  
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    print("video loop")


    while True:
        
        print("  video outer loop")
        try:
            print("  wait for video conn")
            # Accept a connection for video streaming

            conn, addr = server_socket_vid.accept()
            print("  video accepted")
            send_frames(conn, cap)
            print("close video socket")
            conn.shutdown(socket.SHUT_RDWR)
            conn.close()
            video_streaming = False

        except socket.error as e:
            # Handle socket error
            print(f"  An error occurred accept video: {e}")
            # Clean up the connections and continue waiting for next client
        except Exception as e:
            # Handle any other unexpected exceptions
            print(f"  An unexpected error occurred: {e}")
        finally:
            print("  close video socket")
            # Clean up the connections and continue waiting for next client

 
    # Release the camera and close the server sockets
    print("****** SHOULD NEVER GET HERE") 
    print("release camera")
    cap.release()
 
    server_socket_vid.close()

if __name__ == "__main__":
    main() 
