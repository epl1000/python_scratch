import cv2
import socket
import struct
import pickle
import threading
import pigpio


#----SERVO CODE
servo_pin = 18
pi = pigpio.pi()
neutral_pw = 1500
min_pw = 1000
max_pw = 2000
curr_pw = neutral_pw

def ensure_valid_pw(curr_pw):
    MIN_PW = 1000
    MAX_PW = 2000
    
    if curr_pw == 0:
        return curr_pw
    elif curr_pw < MIN_PW:
        return MIN_PW
    elif curr_pw > MAX_PW:
        return MAX_PW
    else:
        return curr_pw
    

def right():
    global curr_pw
    curr_pw = curr_pw + 25
    curr_pw = ensure_valid_pw(curr_pw)
    pi.set_servo_pulsewidth(servo_pin, curr_pw)

def left():
    global curr_pw
    curr_pw = curr_pw - 25
    curr_pw = ensure_valid_pw(curr_pw)
    pi.set_servo_pulsewidth(servo_pin, curr_pw) 

def process_command(command):
    if not command:
        return
    # Implement the logic to control servos based on the received command
    if command == 'left':
        left()
    elif command == 'right':
        right()
    # Add other cases as needed
    
def receive_command(conn):
    while True:
        try:
            # Receive and process the command from the client
            command = conn.recv(1024).decode()
            process_command(command)
        except Exception as e:
            print(f"Error Receiving Commands: {e}")
            break
            
            

# Create a socket object
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Allow resuable socket
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

# Bind the socket to an IP address and port
server_socket.bind(('0.0.0.0', 8485))

# Listen for incoming connections
server_socket.listen(1)

# Accept a connection
conn, addr = server_socket.accept()

# Start thread
receive_thread = threading.Thread(target=receive_command, args=(conn,))
receive_thread.daemon = True
receive_thread.start()

# Open the camera (use 0 for the default camera)
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
cap.set(cv2.CAP_PROP_FPS, 15)

while True:
    # Capture a frame from the camera
    ret, frame = cap.read()
    if not ret:
        break

    # Encode the frame as a JPEG image
    result, frame = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 90])

    # Serialize the JPEG image using pickle
    #data = pickle.dumps(frame)

    # Send the size of the data and the data itself to the client
    conn.sendall(struct.pack(">L", len(frame)))
    conn.sendall(frame)




# Release the camera and close the connection
cap.release()
conn.close()



