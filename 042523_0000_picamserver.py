import cv2
import socket
import struct
import pickle
import threading
import time
import pigpio
import struct
import sys
from enum import Enum, auto

FIRMWARE_REV = 1

start_time = time.time()
prev_time = time.time()

line_num = 1
print_lock = threading.Lock()
            
def PrintTitle():
    print("EddyCam100 Server")
    print("Python Version")
    print(sys.version)
    print("")
    print("%4s %-4s %7s %5s " % ("LINE", "THRD", "TIME", "DT"))
    print("-----------------------------------------------------------------")

# Print values but inlude a line number, time since process start,
# and delta time from previous call to Printf
def Printf(format, *args):
    global line_num
    global prev_time
    global print_lock

    print_lock.acquire()
    t = time.time()
    line_time = t - start_time
    dt = t - prev_time

    print("%4d %-4s %7.3f %5.3f " % (line_num, threading.current_thread().getName(), line_time, dt), end='')
    print(format % args)
    
    prev_time = time.time()
    line_num = line_num + 1
    print_lock.release()

# Log an exception err
def ExcLog(type, err):
    global line_num
    global prev_time
    global print_lock

    print_lock.acquire()
    t = time.time()
    line_time = t - start_time
    dt = t - prev_time
    frame = sys._getframe(1)  # Get frame that called this function
    print("%4d %-4s %7.3f %5.3f *** %s Exception *** in %s() line: %s %s" % (line_num, threading.current_thread().getName(), line_time, dt, type, frame.f_code.co_name, frame.f_lineno, err))
    
    prev_time = time.time()
    line_num = line_num + 1
    print_lock.release()



class OmniCamPacketType(Enum):
    CAM_NO_PACKET = 0
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
        self.firmware_rev = FIRMWARE_REV
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

#vid_event = threading.Event()

#----SERVO CODE
servo_pin_pan = 18
servo_pin_tilt = 12

pi = pigpio.pi()

neutral_pw = 1500

fps = 15
frame_delay = 1 / fps
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
    #Printf("pan");   
    if packet.horz_pan != 0:
        curr_pw_pan = ensure_valid_pw(packet.horz_pan)
        pi.set_servo_pulsewidth(servo_pin_pan, curr_pw_pan)
        
    if packet.vert_pan != 0:
        curr_pw_tilt = ensure_valid_pw(packet.vert_pan)
        pi.set_servo_pulsewidth(servo_pin_tilt, curr_pw_tilt)
   
   
def process_command(conn_com, pack):
    #global vid_event
    global fps
    global jpg_qual
    global frame_delay
  
    # Implement the logic to control servos based on the received command
    if pack.type == OmniCamPacketType.CAM_WRITE_CONFIG.value:
        Printf("WRITE_CONFIG fps=%d jpq_qual=%d", pack.fps, pack.jpg_qual)
        if pack.fps >= 1 and pack.fps <= 30:
            fps = pack.fps
            frame_delay = 1 / fps
        if pack.jpg_qual >= 10 and pack.jpg_qual <= 100:
            jpg_qual = pack.jpg_qual
        
    elif pack.type == OmniCamPacketType.CAM_PAN.value:
        pan(pack)
    elif pack.type == OmniCamPacketType.CAM_READ_CONFIG.value:
         #Printf("CAM_READ_CONFIG")
         pack.horz_pan = pi.get_servo_pulsewidth(servo_pin_pan)
         pack.vert_pan = pi.get_servo_pulsewidth(servo_pin_tilt)
         packed_data = pack_omni_cam_packet(pack)
         conn_com.sendall(packed_data)

    else:
        Printf("Some other kind of command sent")

    
def receive_command(conn_com): 
    
    Printf("recv command start")
    # Determine the expected length of an OmniCamPacket
    expected_length = struct.calcsize(format_str)

    Printf("expected length: %d", expected_length)

    cmd_num = 0
    while True:
        try:
            # Receive and process the command from the client
            # Accumulate received data until the full packet is received
            packet = b''

            try:
                packet = conn_com.recv(expected_length, socket.MSG_WAITALL)
            except Exception as e:
                ExcLog("Cmd Recv", e)
                break
            
            cmd_num = cmd_num + 1
            
            # I don't think this can occur.
            if len(packet) != expected_length:
                Printf("************* Partial command packet len = %d vs %d", len(packet), expected_len)
                # Partial or no data received, handle accordingly
                break
            
            unpacked_packet = unpack_omni_cam_packet(packet)
            process_command(conn_com, unpacked_packet)
        except Exception as e:
            ExcLog("Unexpected", e)
            break
    Printf("  receive command ended")

def command_thread():
   # Create a socket object for command receiving
    server_socket_com = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket_com.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket_com.bind(('0.0.0.0', 56000))
    server_socket_com.listen(1)
    
    Printf("command thread")
    
    while True:
        
        Printf("  outer command loop")
        
        try:    
              # Accept a connection for command receiving
            conn_com, addr1 = server_socket_com.accept()
            
            receive_command(conn_com)
            
            Printf("shutdown command socket")
            #conn_com.shutdown(socket.SHUT_RDWR)
            Printf("close command socket")
            conn_com.close()
            Printf("end command loop");
  
        except socket.error as e:
            # Handle socket error
            ExcLog("Cmd Accept", e)
            # Clean up the connections and continue waiting for next client
        except Exception as e:
            # Handle any other unexpected exceptions
            ExcLog("Cmd Unknown", e)
 


def send_frames(conn, cap):
    #global vid_event
    global fps
    global jpg_qual
    global frame_delay
    
    Printf("  send frames begin")
    Printf("  fps = %d frame_delay=%.3f jpg_qual = %d", fps, frame_delay, jpg_qual)

    packet = OmniCamPacket()

    frame_count = 0
    # Video streaming loop
    while True:
        try:
            #Printf("wait for event set")
            #vid_event.wait()
            
            t1 = time.time()
            #Printf("get frame")
            # send CAM_IMAGE_AVAIL packet type with image size
            ret, frame = cap.read()
            #Printf("end frame")
            frame_count = frame_count+1
                
            #Printf("send frame")
            result, frame = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, jpg_qual])
            packet.type = OmniCamPacketType.CAM_IMAGE_AVAIL.value
            packet.size = len(frame)
            packed_data = pack_omni_cam_packet(packet)
            conn.sendall(packed_data)
            conn.sendall(frame)
            t2 = time.time()
            dt = t2 - t1
            adjusted_delay = frame_delay - dt
     
            #Printf("dt=%.3f", dt)
            if adjusted_delay > 0:
                time.sleep(adjusted_delay)
 
        except socket.error as e:
            # Handle socket error
            ExcLog("Send Frame", e)
            break
        except Exception as e:
            # Handle any other unexpected exceptions
            ExcLog("Unknown", e)
            break
        
    Printf("send_frames return");

def create_camera():    
    Printf("create camera")
    cap = cv2.VideoCapture(0)  
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    Printf("get dummy frame")
    ret, frame = cap.read()
    Printf("create camera done")
    return cap


def main():
    
    PrintTitle()
    
    threading.current_thread().setName("Main")
    
    # Start thread for receiving commands
    #receive_thread_lock.acquire()
    receive_thread = threading.Thread(target=command_thread, name="Cmd")
    receive_thread.daemon = True
    receive_thread.start()

 
    # Create a socket object for video streaming
    server_socket_vid = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket_vid.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket_vid.bind(('0.0.0.0', 56100))
    server_socket_vid.listen(1)
 

    #  Create camera capture object
    cap = create_camera()
 
    Printf("video loop")

    ExcLog("Dummy", "dummy err")
    
    while True:
        
        Printf("video outer loop")
        try:
            Printf("wait for video conn")
            # Accept a connection for video streaming

            conn, addr = server_socket_vid.accept()
            conn.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 256 * 1024)
            sock_buffsize = conn.getsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF)
            Printf("SND_BUF size = %d", sock_buffsize)
            Printf("video accepted")
            send_frames(conn, cap)
            Printf("close video socket")
            conn.shutdown(socket.SHUT_RDWR)
            conn.close()
 
        except socket.error as e:
            # Handle socket error
            ExcLog("Video Accept", e)
            # Clean up the connections and continue waiting for next client
        except Exception as e:
            # Handle any other unexpected exceptions
            ExcLog("Unexpected", e)
  
 
    # Release the camera and close the server sockets
    print("****** SHOULD NEVER GET HERE") 
    print("release camera")
    cap.release()
 
    server_socket_vid.close()

if __name__ == "__main__":
    main() 

