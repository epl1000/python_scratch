import struct
from enum import Enum, auto
import socket
import os

# Define the server address and port
server_address = ('192.168.2.37', 8080)
default_directory = "/home/pi"

class TransferPacketType(Enum):
    TEST = 0
    FIRST_SEND = auto()
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
    return struct.pack(format_str, packet.byimport struct
from enum import Enum, auto
import socket
import os

# Define the server address and port
server_address = ('192.168.2.37', 8080)
default_directory = "/home/pi"

class TransferPacketType(Enum):
    TEST = 0
    FIRST_SEND = auto()
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



def save_file(file_name, file_data):
    file_path = os.path.join(default_directory, file_name)
    with open(file_path, 'wb') as file:
        file.write(file_data)

def start_server():
    
    try:   
        # Create a socket object
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # Bind the socket to the server address and port
        server_socket.bind(server_address)
        # Listen for incoming connections
        server_socket.listen()

        while True:
            # Accept a connection from a client
            client_socket, client_address = server_socket.accept()
            print(f"Connection from: {client_address}")
       
            # packetized header code
            expected_length = struct.calcsize(format_str)
            packet = client_socket.recv(expected_length, socket.MSG_WAITALL)
            unpacked_packet = unpack_transfer_packet(packet)
            file_length = unpacked_packet.size
            file_name = unpacked_packet.name.decode('utf-8')

            print(f"Receiving file: {unpacked_packet.name} (TYPE: {unpacked_packet.type})")
            
            # Receive the file data from the client
            file_data = client_socket.recv(file_length)
            
            # VERIFY FILE 
         
            # Send file data back to client for verification
            unpacked_packet.size = len(file_data)
            unpacked_packet.name = file_name.encode()
            unpacked_packet.type = TransferPacketType.TRY_VERIFY.value
            header = pack_transfer_packet(unpacked_packet)
            
            # Send Header
            client_socket.sendall(header)
            print("sent file header")
            # Send File
            client_socket.sendall(file_data)
            print("sent file back for verification")       
            
            # WAIT FOR VERIFICATION ----------------------
            
            # packetized header code
            expected_length = struct.calcsize(format_str)
            packet = client_socket.recv(expected_length, socket.MSG_WAITALL)
            unpacked_packet = unpack_transfer_packet(packet)
            
            if unpacked_packet.type == TransferPacketType.SUCC_VERIFY.value:
                print("Verify Process Succeded, Save File")
                # Save the received file to the default directory
                save_file(file_name, file_data)
                # Next step is run or even kill existing process then run
            else:
                print("Verify Process Failed, Not Saving File")
                

            # Close the client connection
            client_socket.close()
        
    except socket.error as e:
        print(f"Socket error ocurred: {e}")
    except socket.timeout as e:
        print(f"Socket timeout ocurred: {e}")
    except Exception as e:
        print(f"An unexpected error ocurred {e}")

# Start the server
start_server()
te_order, packet.type, padded_name, packet.firmware_rev, packet.size)

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



def save_file(file_name, file_data):
    file_path = os.path.join(default_directory, file_name)
    with open(file_path, 'wb') as file:
        file.write(file_data)

def start_server():
    
    try:   
        # Create a socket object
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # Bind the socket to the server address and port
        server_socket.bind(server_address)
        # Listen for incoming connections
        server_socket.listen()

        while True:
            # Accept a connection from a client
            client_socket, client_address = server_socket.accept()
            print(f"Connection from: {client_address}")
       
            # packetized header code
            expected_length = struct.calcsize(format_str)
            packet = client_socket.recv(expected_length, socket.MSG_WAITALL)
            unpacked_packet = unpack_transfer_packet(packet)
            file_length = unpacked_packet.size
            file_name = unpacked_packet.name.decode('utf-8')

            print(f"Receiving file: {unpacked_packet.name} (TYPE: {unpacked_packet.type})")
            
            # Receive the file data from the client
            file_data = client_socket.recv(file_length)
            
            # VERIFY FILE 
         
            # Send file data back to client for verification
            unpacked_packet.size = len(file_data)
            unpacked_packet.name = file_name.encode()
            unpacked_packet.type = TransferPacketType.TRY_VERIFY.value
            header = pack_transfer_packet(unpacked_packet)
            
            # Send Header
            client_socket.sendall(header)
            print("sent file header")
            # Send File
            client_socket.sendall(file_data)
            print("sent file back for verification")       
            
            # WAIT FOR VERIFICATION ----------------------
            
            # packetized header code
            expected_length = struct.calcsize(format_str)
            packet = client_socket.recv(expected_length, socket.MSG_WAITALL)
            unpacked_packet = unpack_transfer_packet(packet)
            
            if unpacked_packet.type == TransferPacketType.SUCC_VERIFY.value:
                print("Verify Process Succeded, Save File")
                # Save the received file to the default directory
                save_file(file_name, file_data)
                # Next step is run or even kill existing process then run
            else:
                print("Verify Process Failed, Not Saving File")
                

            # Close the client connection
            client_socket.close()
        
    except socket.error as e:
        print(f"Socket error ocurred: {e}")
    except socket.timeout as e:
        print(f"Socket timeout ocurred: {e}")
    except Exception as e:
        print(f"An unexpected error ocurred {e}")

# Start the server
start_server()