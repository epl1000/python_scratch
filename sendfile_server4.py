import socket
import os

# Define the server address and port
server_address = ('10.0.0.19', 8080)
default_directory = "/home/edwardlopez/Python3x"

def save_file(file_name, file_data):
    file_path = os.path.join(default_directory, file_name)
    with open(file_path, 'wb') as file:
        file.write(file_data)

def start_server():
    # Create a socket object
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Bind the socket to the server address and port
    server_socket.bind(server_address)
    # Listen for incoming connections
    server_socket.listen()

    while True:
        # Accept a connection from a client
        client_socket, client_address = server_socket.accept()
        print(f"Connection from: {client_address}")

        # Receive the header from the client
        header = client_socket.recv(1024).decode()
        file_length = int(header[:10])
        file_name = header[10:]

        print(f"Receiving file: {file_name} (Length: {file_length} bytes)")

        # Receive the file data from the client
        file_data = client_socket.recv(file_length)

        # Save the received file to the default directory
        save_file(file_name, file_data)

        # Close the client connection
        client_socket.close()

# Start the server
start_server()

