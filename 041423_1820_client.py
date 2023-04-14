from enum import Enum, auto
import cv2
import socket
import struct
import time
import numpy as np
import tkinter as tk
from PIL import Image, ImageTk
import threading

class OmniCamPacketType(Enum):
    CAM_NO_PACKET = 0
    CAM_START = auto()
    CAM_STOP = auto()
    CAM_IMAGE_AVAIL = auto()
    CAM_WRITE_CONFIG = auto()
    CAM_READ_CONFIG = auto()
    CAM_PAN = auto()
    NUM_CAM_PACKET_TYPE = auto()

BYTE_ORDER_FLAG = 0x12345678

class OmniCamPacket:
    def __init__(self, type):
        self.byte_order = BYTE_ORDER_FLAG
        self.type = type
        self.firmware_rev = 1
        self.horz_pan = 0
        self.vert_pan = 0
        self.fps = 0
        self.size = 0

format_str = 'Iiiiiii'

def pack_omni_cam_packet(packet):
    return struct.pack(format_str, packet.byte_order, packet.type, packet.firmware_rev,
                       packet.horz_pan, packet.vert_pan, packet.fps, packet.size)

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

packet = OmniCamPacket(type=OmniCamPacketType.CAM_PAN.value)
packet_vid = OmniCamPacket(type=OmniCamPacketType.CAM_IMAGE_AVAIL.value)

class App:
    def __init__(self, window):
        self.window = window
        self.window.title("RPI Webcam Viewer")
        self.window.protocol("WM_DELETE_WINDOW", self.on_close)
        self.video_canvas = tk.Canvas(window, width=640, height=480)
        self.video_canvas.pack()
        self.create_buttons()
        self.image_item = self.video_canvas.create_image(0, 0, image=None, anchor=tk.NW)
        self.start_video_receiving()
        self.connect_to_server()
        self.pan_state = "NONE"  # State variable to track desired pan direction
        self.pan_thread = threading.Thread(target=self.pan_loop, daemon=True)
        self.pan_thread.start()

    def create_buttons(self):
        # Create a frame to contain the buttons
        button_frame = tk.Frame(self.window)
        button_frame.pack(fill=tk.X)

        # Configure columns to expand and fill available space
        button_frame.columnconfigure(0, weight=1)
        button_frame.columnconfigure(1, weight=1)

        button1 = tk.Button(button_frame, text="Left", command=self.on_button1_click)
        button2 = tk.Button(button_frame, text="Right", command=self.on_button2_click)
        button3 = tk.Button(button_frame, text="STOP VIDEO FEED", command=self.on_button3_click)
        button4 = tk.Button(button_frame, text="START VIDEO FEED", command=self.on_button4_click)

        # Use grid geometry manager within the button_frame
        button1.grid(row=0, column=0, sticky="ew")
        button2.grid(row=0, column=1, sticky="ew")
        button3.grid(row=1, column=0, sticky="ew")
        button4.grid(row=1, column=1, sticky="ew")

        # Bindings for button down and up events
        button1.bind('<ButtonPress-1>', self.on_button1_down)
        button1.bind('<ButtonRelease-1>', self.on_button1_up)
        button2.bind('<ButtonPress-1>', self.on_button2_down)
        button2.bind('<ButtonRelease-1>', self.on_button2_up)

    def update_video_canvas(self, frame):
        image = Image.fromarray(frame)
        photo = ImageTk.PhotoImage(image)
        self.video_canvas.create_image(0, 0, image=photo, anchor=tk.NW)
        self.window.update_idletasks()  # Fix here
        self.window.update()

    def connect_to_server(self):
        max_retries = 5  # Maximum number of retries
        retry_interval = 3  # Time to wait between retries (in seconds)
        for attempt in range(max_retries):
            try:
                self.command_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.command_socket.connect(('192.168.2.36', 8486))
                print("Successfully connected to server.")
                return  # Successful connection
            except ConnectionRefusedError as e:
                print(f"Connection attempt {attempt + 1} failed. Retrying...")
                time.sleep(retry_interval)
        print(f"Failed to connect to server after {max_retries} attempts.")

    def on_button1_click(self):
        print("Left button clicked")

    def on_button2_click(self):
        print("Right button clicked")

    def on_button3_click(self):
        packet.type = OmniCamPacketType.CAM_STOP.value
        packed_data = pack_omni_cam_packet(packet)
        self.command_socket.sendall(packed_data)

    def on_button4_click(self):
        packet.type = OmniCamPacketType.CAM_START.value
        packed_data = pack_omni_cam_packet(packet)
        self.command_socket.sendall(packed_data)

    def on_button1_down(self, event):
        print("Left button is down")
        self.pan_state = "LEFT"

    def on_button1_up(self, event):
        print("Left button is up")
        self.pan_state = "NONE"

    def on_button2_down(self, event):
        print("Right button is down")
        self.pan_state = "RIGHT"

    def on_button2_up(self, event):
        print("Right button is up")
        self.pan_state = "NONE"

    # Loop to continuously send pan commands based on the current state
    def pan_loop(self):
        while True:
            if self.pan_state == "LEFT":
                packet.horz_pan = 1
                packet.type = OmniCamPacketType.CAM_PAN.value
                packed_data = pack_omni_cam_packet(packet)
                self.command_socket.sendall(packed_data)
            elif self.pan_state == "RIGHT":
                packet.horz_pan = -1
                packet.type = OmniCamPacketType.CAM_PAN.value
                packed_data = pack_omni_cam_packet(packet)
                self.command_socket.sendall(packed_data)
            elif self.pan_state == "NONE":
                packet.horz_pan = 0

            # Sleep for a short duration (e.g., 0.1 seconds) to prevent command flooding
            time.sleep(0.1)

    def on_close(self):
        self.command_socket.close()
        self.window.destroy()

    def start_video_receiving(self):
        self.video_thread = threading.Thread(target=self.receive_video, daemon=True)
        self.video_thread.start()

    def receive_video(self):
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect(('192.168.2.36', 8485))
        data = b''
        payload_size = struct.calcsize(">L")
        frame_counter = 0
        start_time = time.time()
        delta_time = 0

        while True:
            try:
                expected_length = struct.calcsize(format_str)
                packet_vid_data = b''
                while len(packet_vid_data) < expected_length:
                    chunk = client_socket.recv(expected_length - len(packet_vid_data))
                    packet_vid_data += chunk

                if len(packet_vid_data) != expected_length:
                    print("Received partial or no data")
                    break

                packet_vid = unpack_omni_cam_packet(packet_vid_data)
                if packet_vid.type == OmniCamPacketType.CAM_IMAGE_AVAIL.value:
                    msg_size = packet_vid.size
                else:
                    # Display blue screen with message
                    frame = np.zeros((480, 640, 3), dtype=np.uint8)
                    frame[:, :] = (255, 0, 0)  # Blue color
                    cv2.putText(frame, "NO VIDEO FEED", (200, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                    image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                    photo = ImageTk.PhotoImage(image)
                    self.video_canvas.itemconfig(self.image_item, image=photo)
                    self.video_canvas.image = photo
                    msg_size = 0

                if msg_size > 0:
                    image_data = b''
                    while len(image_data) < msg_size:
                        remaining_bytes = msg_size - len(image_data)
                        try:
                            image_data += client_socket.recv(min(65536, remaining_bytes))
                        except socket.error as e:
                            print(f"An error occurred while receiving data: {e}")
                            break

                    frame = np.frombuffer(image_data, dtype=np.uint8)
                    frame = cv2.imdecode(frame, cv2.IMREAD_COLOR)

                    frame_counter += 1
                    elapsed_time = time.time() - start_time
                    cv2.putText(frame, f"Frame: {frame_counter}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 50), 2)
                    cv2.putText(frame, f"Elapsed Time: {elapsed_time:.2f} s", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 1,
                                (0, 255, 50), 2)

                    #cv2.imshow('Received Frame', frame)
                    # Display the frame in the Tkinter window
                    #self.update_video_canvas(frame)
                    image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                    photo = ImageTk.PhotoImage(image)
                    self.video_canvas.itemconfig(self.image_item, image=photo)
                    self.video_canvas.image = photo


                    delta_time = elapsed_time - delta_time
                    if delta_time > 1:
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


# Initialize the application window
window = tk.Tk()
app = App(window)

# Start the Tkinter event loop in the main thread
window.mainloop()


