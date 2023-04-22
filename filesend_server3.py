import socket
import os
import tkinter as tk
from tkinter import filedialog

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

# Receive the fixed-size file length (10 bytes)
file_length_bytes = client_socket.recv(10)
file_length = int(file_length_bytes.decode().strip())

# Receive the rest of the header to extract the file name
file_name = b''
while len(file_name) < file_length:
    file_name += client_socket.recv(file_length - len(file_name))

# Convert the file name to a string
file_name = file_name.decode().strip()

# Receive the file data
file_data = b''
while len(file_data) < file_length:
    file_data += client_socket.recv(file_length - len(file_data))

def save_received_file(file_name, file_data):
    # Open file save dialog
    root = tk.Tk()
    root.withdraw()
    save_path = filedialog.asksaveasfilename(defaultextension=".txt",
                                             initialfile=file_name,
                                             filetypes=[("Text files", "*.txt")])
    if save_path:
        # Save the file
        with open(save_path, 'wb') as file:
            file.write(file_data)

# Save the received file
save_received_file(file_name, file_data)

# Close the client socket
client_socket.close()

# Close the server socket
server_socket.close()
