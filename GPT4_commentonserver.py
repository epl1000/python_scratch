
In the provided server code, the issue of the server not working after a client disconnects and reconnects may be due 
to the handling of client disconnections. When a client disconnects, the server should be able to detect this and cleanly 
close the associated sockets before waiting for new client connections.

To address this issue, consider the following changes:

    Use a dedicated Event object to signal when the receive_command thread should exit. This way, when the video streaming loop ends 
    due to a client disconnection or socket error, the receive_command thread can also be stopped cleanly.

    In the receive_command function, check whether the client has disconnected by examining the chunk received from the recv method. 
    If an empty chunk is received, it indicates that the client has disconnected, and the receive_command thread should exit.

    Use the join method to ensure the receive_command thread has exited before accepting new client connections.

Here's the modified code with these changes:

python

# (Other imports and code omitted for brevity)

# Add a new Event object to signal when the receive_command thread should exit
receive_command_exit_event = threading.Event()

def receive_command_wrapper(conn_com):
    try:
        receive_command(conn_com)
    finally:
        receive_thread_lock.release()

def receive_command(conn_com):
    expected_length = struct.calcsize(format_str)
    
    while not receive_command_exit_event.is_set():
        try:
            packet = b''
            while len(packet) < expected_length:
                chunk = conn_com.recv(expected_length - len(packet))
                if not chunk:
                    return  # Client disconnected
                packet += chunk
            
            if len(packet) != expected_length:
                return  # Partial or no data received
            
            unpacked_packet = unpack_omni_cam_packet(packet)
            # (Rest of the code in receive_command)
        except Exception as e:
            print(f"Error Receiving Commands: {e}")
            break

def main():
    # (Rest of the code in main before the while True loop)

    while True:
        try:
            conn_com, addr1 = server_socket_com.accept()

            receive_thread_lock.acquire()
            receive_command_exit_event.clear()
            receive_thread = threading.Thread(target=receive_command_wrapper, args=(conn_com,))
            receive_thread.daemon = True
            receive_thread.start()

            conn, addr = server_socket_vid.accept()

            while True:
                # (Rest of the code in the video streaming loop)

        except socket.error as e:
            print(f"An error occurred while connecting to client: {e}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
        finally:
            # Signal the receive_command thread to exit and wait for it to finish
            receive_command_exit_event.set()
            receive_thread.join()

            # Clean up the connections
            conn_com.close()
            conn.close()

    # (Rest of the code in main after the while True loop)

if __name__ == "__main__":
    main()

These changes should allow the server to handle client disconnections gracefully and be ready to accept new client connections.
