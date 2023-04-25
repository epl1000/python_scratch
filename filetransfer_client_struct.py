import socket
import struct
from enum import Enum, auto
import tkinter as tk
from tkinter import filedialog


class TransferPacketType(Enum):
    TEST = 0
    NEW_REV = auto()
    TRY_VERIFY = auto()
    SUCC_VERIFY = auto()
    FAIL_VERIFY = auto()
    SEND_CONFIG = auto()

BYTE_ORDER_FLAG = 0x12345678

class TransferPacket:
    def __init__(self, type, name=b'file_name', firmware_rev=1, size=0):
        self.byte_order = BYTE_ORDER_FLAG
        self.type = type
        self.name = name
        self.firmware_rev = firmware_rev
        self.size = size

format_str = 'Ii64sii'

def pack_transfer_packet(packet):
    # Pad the 'name' field with null bytes to the specified fixed length (64 bytes)
    padded_name = packet.name.ljust(64, b'\x00')
    return struct.pack(format_str, packet.byte_order, packet.type, padded_name, packet.firmware_rev, packet.size)

def unpack_transfer_packet(data):
    unpacked_data = struct.unpack(format_str, data)
    # Extract the fields from the unpacked data
    byte_order, type, name, firmware_rev, size = unpacked_data
    # Remove trailing null bytes from the 'name' field
    name = name.rstrip(b'\x00')
    # Create an instance of TransferPacket with the extracted fields
    packet = TransferPacket(type=type, name=name, firmware_rev=firmware_rev, size=size)
    packet.byte_order = byte_order
    return packet

packet = TransferPacket(type=TransferPacketType.TEST.value)


def send_file(file_path):
    # Create a socket object
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Define the server address and port
    server_address = ('192.168.2.36', 8080)

    # Connect to the server
    client_socket.connect(server_address)

    # Open the file and read its content
    with open(file_path, 'rb') as file:
        file_data = file.read()
        file_name = file_path.split('/')[-1]
        print(f"File Name: {file_name}")
        file_length = len(file_data)
        print(f"file length: {file_length}")
        packet.name = file_name
        packet.size = file_length

        # Create header with file length (fixed-size) and file name
        #header = f"{file_length:010d}{file_name}".encode()
        header = pack_transfer_packet(packet)

        # Send header to the server
        client_socket.sendall(header)

        # Send file data to the server
        client_socket.sendall(file_data)

    # Close the socket
    client_socket.close()

def select_and_send_file():
    # Open file select dialog
    root = tk.Tk()
    root.withdraw()
    initial_directory = "C:\\Users\\17249\\AppData\\Roaming\\JetBrains\\PyCharmCE2021.3\\scratches\\"

    file_path = filedialog.askopenfilename(
        initialdir=initial_directory,
        filetypes=[("Python files", "*.py"), ("Text files", "*.txt")])

    if file_path:
        send_file(file_path)

# Select and send the file
select_and_send_file()
