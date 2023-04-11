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
packet = OmniCamPacket(type=2)
packet.horz_pan = 10
packet.vert_pan = 20
packet.fps = 30
packet.size = 40

packed_data = pack_omni_cam_packet(packet)
print("Packed data:", packed_data)

unpacked_packet = unpack_omni_cam_packet(packed_data)
print("Unpacked packet:", unpacked_packet.__dict__)
