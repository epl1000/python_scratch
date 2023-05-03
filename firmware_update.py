
import struct
from enum import Enum, auto
import socket
import os
import logging


# Name log file same as py file but with log ext
logfile_name, _ = os.path.splitext(__file__)
logging.basicConfig(filename=logfile_name+'.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Define the server address and port
server_address = ('192.168.2.37', 8080)
default_directory = "/home/pi/eddycam"

print(__file__)

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
        file.flush()
    logging.info(f"Saved file: {file_name}")
        
def read_file(file_name, file_data):
    file_path = os.path.join(default_directory, file_name)
    with open(file_path, 'rb') as file:
        file_data = file.read()
    logging.info(f"Read file: {file_name}")
    

def start_server():
    
    logging.info('START SERVER===============================')
    
    try:   
        
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket.bind(server_address)
            server_socket.listen()

            while True:
                # Accept a connection from a client
                with server_socket.accept()[0] as client_socket:
                    #print(f"Connection from: {client_address}")
                    logging.info('Connection Made from client')
                    
                    # packetized header code
                    expected_length = struct.calcsize(format_str)
                    packet = client_socket.recv(expected_length, socket.MSG_WAITALL)
                    unpacked_packet = unpack_transfer_packet(packet)
                    file_length = unpacked_packet.size
                    file_name = unpacked_packet.name.decode('utf-8')
                    
                    # Only perform handshake if packet type is correct
                    if unpacked_packet.type == TransferPacketType.FIRST_SEND.value and file_name != __file__:

                        print(f"Receiving file: {file_name} (TYPE: {unpacked_packet.type})")
                        logging.info(f"Receiving file: {file_name} (TYPE: {unpacked_packet.type})")
                        # Receive the file data from the client
                        file_data = client_socket.recv(file_length, socket.MSG_WAITALL)
                        
                        # Save file and read it back before verification
                        save_file(file_name, file_data)
                        read_file(file_name, file_data)          
                     
                        # Send file data back to client for verification
                        unpacked_packet.size = len(file_data)
                        unpacked_packet.name = file_name.encode()
                        unpacked_packet.type = TransferPacketType.TRY_VERIFY.value
                        header = pack_transfer_packet(unpacked_packet)
                        
                        # Send Header
                        client_socket.sendall(header)
                        print("sent file header")
                        logging.info('Sent file header')
                        # Send File
                        client_socket.sendall(file_data)
                        print("sent file back for verification")
                        logging.info('Sent file back for verification')
                        
                        # Receive verification results                   
                        expected_length = struct.calcsize(format_str)
                        packet = client_socket.recv(expected_length, socket.MSG_WAITALL)
                        unpacked_packet = unpack_transfer_packet(packet)
                        
                        if unpacked_packet.type == TransferPacketType.SUCC_VERIFY.value:
                            print("Verify Succeded, Save File")
                            logging.info('Verify Succeded')
                        else:
                            print("Verify Process Failed")
                            logging.info('Verify Failed')
                    elif file_name == __file__:
                        logging.info(f"ERROR - Receiving file: {file_name} Same name as Transfer Program {__file__}")
                        print(f"ERROR - Receiving file: {file_name} Same name as Transfer Program {__file__}")
                    
                    elif unpacked_packet.type != TransferPacketType.FIRST_SEND.value:
                        logging.info(f"ERROR - Receiving file: {unpacked_packet.name} (TYPE: {unpacked_packet.type}) IS INCORRECT")
                        print(f"ERROR - Receiving file: {unpacked_packet.name} (TYPE: {unpacked_packet.type}) IS INCORRECT")
                            

                    # Close the client connection
                    client_socket.close()
                    logging.info('Client connection closed___________________')
    except socket.timeout as e:
        print(f"Socket timeout ocurred: {e}")
        logging.info(f"Socket timeout ocurred: {e}")       
    except socket.error as e:
        print(f"Socket error ocurred: {e}")
        logging.info(f"Socket error ocurred: {e}")

    except Exception as e:
        print(f"An unexpected error ocurred {e}")
        logging.info(f"An unexpected error ocurred: {e}")

# Start the server
start_server()
