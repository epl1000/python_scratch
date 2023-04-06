import socket

while True:
    try:
        # Capture a frame from the camera
        ret, frame = cap.read()
        if not ret:
            break

        # Try to encode the frame as a JPEG image
        try:
            result, frame = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        except cv2.error as e:
            # Handle cv2 error
            print(f"An error occurred while encoding the frame: {e}")
            break

        # Try to send the size of the data and the data itself to the client
        try:
            conn.sendall(struct.pack(">L", len(frame)))
            conn.sendall(frame)
        except socket.error as e:
            # Handle socket error
            print(f"An error occurred while sending data: {e}")
            break

    except Exception as e:
        # Handle any other unexpected exceptions
        print(f"An unexpected error occurred: {e}")
        break

# Continue with the rest of the code...

