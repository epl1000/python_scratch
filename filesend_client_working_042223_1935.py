import socket
import tkinter as tk
from tkinter import filedialog

def send_file(file_path):
    # Create a socket object
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Define the server address and port
    server_address = ('10.0.0.19', 8080)

    # Connect to the server
    client_socket.connect(server_address)

    # Open the file and read its content
    with open(file_path, 'rb') as file:
        file_data = file.read()
        file_name = file_path.split('/')[-1]
        print(f"File Name: {file_name}")
        file_length = len(file_data)
        print(f"file length: {file_length}")

        # Create header with file length (fixed-size) and file name
        header = f"{file_length:010d}{file_name}".encode()

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
