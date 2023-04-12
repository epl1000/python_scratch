def receive_command():
    # Create a socket object
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(('0.0.0.0', 8486))
    server_socket.listen(1)
    conn_com, addr1 = server_socket.accept()
    
    # Determine the expected length of an OmniCamPacket
    expected_length = struct.calcsize(format_str)
    
    while True:
        print("I'm here")
        time.sleep(1)
        try:
            # Receive and process the command from the client
            # Accumulate received data until the full packet is received
            packet = b''
            while len(packet) < expected_length:
                chunk = conn_com.recv(expected_length - len(packet))
                if not chunk:
                    break  # Client disconnected
                packet += chunk
            
            if len(packet) != expected_length:
                # Partial or no data received, handle accordingly
                break
            
            unpacked_packet = unpack_omni_cam_packet(packet)
            print(f"Packet is {unpacked_packet.horz_pan}")
            #process_command(command)
        except Exception as e:
            print(f"Error Receiving Commands: {e}")
            break

