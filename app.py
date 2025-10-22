from flask import Flask, render_template, Response
from flask_socketio import SocketIO, emit
import cv2
import mediapipe as mp
import numpy as np
import threading
import time

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# Initialize MediaPipe Pose
mp_pose = mp.solutions.pose
pose = mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)
mp_drawing = mp.solutions.drawing_utils

# Global variables
current_presence_status = "outside"  # "inside" or "outside"
latest_frame = None
frame_lock = threading.Lock()
camera_active = True

# Define the detection rectangle (as percentage of frame dimensions)
# Format: (x_min, y_min, x_max, y_max) where values are 0.0 to 1.0
DETECTION_RECT = (0.2, 0.15, 0.8, 0.85)  # Centered rectangle covering 60% width and 70% height

@app.route('/')
def index():
    return render_template('index.html')

def is_person_in_rectangle(pose_landmarks, rect):
    """
    Check if the person's center of mass is inside the detection rectangle
    """
    if not pose_landmarks:
        return False
    
    # Get key body landmarks to determine center of mass
    landmarks_to_check = [
        mp_pose.PoseLandmark.LEFT_SHOULDER,
        mp_pose.PoseLandmark.RIGHT_SHOULDER,
        mp_pose.PoseLandmark.LEFT_HIP,
        mp_pose.PoseLandmark.RIGHT_HIP,
    ]
    
    x_coords = []
    y_coords = []
    
    for landmark_id in landmarks_to_check:
        landmark = pose_landmarks.landmark[landmark_id]
        # Only consider visible landmarks
        if landmark.visibility > 0.5:
            x_coords.append(landmark.x)
            y_coords.append(landmark.y)
    
    if not x_coords:
        return False
    
    # Calculate center of mass
    center_x = sum(x_coords) / len(x_coords)
    center_y = sum(y_coords) / len(y_coords)
    
    # Check if center is inside rectangle
    x_min, y_min, x_max, y_max = rect
    return x_min <= center_x <= x_max and y_min <= center_y <= y_max

def camera_loop():
    """Single camera capture loop that handles both detection and video feed"""
    global current_presence_status, latest_frame, camera_active
    
    cap = cv2.VideoCapture(0)
    
    while camera_active:
        success, frame = cap.read()
        if not success:
            time.sleep(0.1)
            continue
        
        # Flip frame horizontally for mirror effect
        frame = cv2.flip(frame, 1)
        
        h, w, _ = frame.shape
        
        # Draw the detection rectangle on the frame
        rect_color = (0, 255, 0)  # Green
        x_min, y_min, x_max, y_max = DETECTION_RECT
        top_left = (int(x_min * w), int(y_min * h))
        bottom_right = (int(x_max * w), int(y_max * h))
        cv2.rectangle(frame, top_left, bottom_right, rect_color, 3)
        
        # Process frame for pose detection
        image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = pose.process(image_rgb)

        presence_status = "outside"

        if results.pose_landmarks:
            # Draw pose landmarks on the frame
            mp_drawing.draw_landmarks(
                frame, 
                results.pose_landmarks, 
                mp_pose.POSE_CONNECTIONS,
                mp_drawing.DrawingSpec(color=(245,117,66), thickness=2, circle_radius=2),
                mp_drawing.DrawingSpec(color=(245,66,230), thickness=2, circle_radius=2)
            )
            
            # Check if person is inside the rectangle
            if is_person_in_rectangle(results.pose_landmarks, DETECTION_RECT):
                presence_status = "inside"
                # Change rectangle color to indicate detection
                cv2.rectangle(frame, top_left, bottom_right, (0, 255, 255), 3)  # Yellow when person inside

        # Only emit if status changed
        if presence_status != current_presence_status:
            current_presence_status = presence_status
            socketio.emit('presence_status', {'status': presence_status})
            print(f"Presence status: {presence_status}")
        
        # Store the latest frame for video feed
        with frame_lock:
            latest_frame = frame.copy()
        
        time.sleep(0.033)  # ~30 fps
    
    cap.release()

def gen_frames():
    """Generator that yields frames from the shared camera feed"""
    global latest_frame
    
    while True:
        with frame_lock:
            if latest_frame is None:
                time.sleep(0.1)
                continue
            frame = latest_frame.copy()
        
        # Encode frame as JPEG
        ret, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@socketio.on('connect')
def handle_connect():
    print('Client connected')
    emit('presence_status', {'status': current_presence_status})

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

if __name__ == '__main__':
    # Start camera loop in a separate thread
    camera_thread = threading.Thread(target=camera_loop, daemon=True)
    camera_thread.start()
    
    # Give camera time to initialize
    time.sleep(1)
    
    socketio.run(app, debug=True, use_reloader=False)