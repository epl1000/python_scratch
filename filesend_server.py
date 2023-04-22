
import socket
import os

# Create a socket object
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Define the server address and port
server_address = ('localhost', 8080)

# Bind the socket to the address
server_socket.bind(server_address)

# Listen for incoming connections
server_socket.listen(1)

# Accept a client connection
client_socket, client_address = server_socket.accept()

# Receive the header
header = client_socket.recv(1024).decode().strip()
file_name, file_extension, file_length = header.split(',')

# Receive the file data
file_data = client_socket.recv(int(file_length))

# Save the file
with open(os.path.join('received_files', file_name), 'wb') as file:
    file.write(file_data)

# If it's a Python file, launch it
if file_extension == 'py':
    os.system(f"python {os.path.join('received_files', file_name)}")

# Close the client socket
client_socket.close()

# Close the server socket
server_socket.close()
