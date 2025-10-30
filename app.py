from flask import Flask, render_template, Response
from flask_socketio import SocketIO, emit
import cv2
import mediapipe as mp
import numpy as np
import threading
import time

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", ping_timeout=60, ping_interval=25)

# Initialize MediaPipe Pose
mp_pose = mp.solutions.pose
pose = mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)
mp_drawing = mp.solutions.drawing_utils

# Global variables
current_presence_status = "outside"  # "inside" or "outside"
latest_frame = None
frame_lock = threading.Lock()
camera_active = True

# Detection smoothing - prevent flickering
detection_history = []
DETECTION_HISTORY_SIZE = 8  # Number of frames to track
REQUIRED_CONFIDENCE = 0.65  # 65% of frames must agree to change status

# Define the detection rectangle (as percentage of frame dimensions)
# Format: (x_min, y_min, x_max, y_max) where values are 0.0 to 1.0
DETECTION_RECT = (0.4, 0.15, 0.6, 0.85)  # Centered rectangle covering 60% width and 70% height

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/viewer')
def viewer():
    return render_template('viewer.html')

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

def get_smoothed_presence(current_detection):
    """
    Smooth detection over multiple frames to prevent flickering
    Only change status if we have consistent readings
    """
    global detection_history, current_presence_status
    
    # Add current detection to history
    detection_history.append(current_detection)
    
    # Keep only recent history
    if len(detection_history) > DETECTION_HISTORY_SIZE:
        detection_history.pop(0)
    
    # Need minimum history before making decisions
    if len(detection_history) < DETECTION_HISTORY_SIZE:
        return current_presence_status
    
    # Count "inside" detections
    inside_count = sum(1 for d in detection_history if d == "inside")
    inside_ratio = inside_count / len(detection_history)
    
    # Only change status if we have strong confidence
    if inside_ratio >= REQUIRED_CONFIDENCE:
        return "inside"
    elif inside_ratio <= (1 - REQUIRED_CONFIDENCE):
        return "outside"
    else:
        # Not confident either way, keep current status
        return current_presence_status    

def camera_loop():
    """Single camera capture loop with external webcam support"""
    global current_presence_status, latest_frame, camera_active
    
    cap = cv2.VideoCapture(1)  # External webcam
    
    # Configure camera for stability
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    cap.set(cv2.CAP_PROP_FPS, 30)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    # Warm up camera
    print("Warming up camera...")
    for i in range(10):
        cap.read()
        time.sleep(0.1)
    print("Camera ready!")
    
    frame_count = 0
    last_successful_frame = None
    consecutive_failures = 0
    
    while camera_active:
        success, frame = cap.read()
        
        if not success:
            consecutive_failures += 1
            print(f"Frame read failed. Consecutive failures: {consecutive_failures}")
            
            if consecutive_failures > 30:
                print("Reconnecting camera...")
                cap.release()
                time.sleep(1)
                cap = cv2.VideoCapture(1)
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                cap.set(cv2.CAP_PROP_FPS, 30)
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                consecutive_failures = 0
                continue
            
            if last_successful_frame is not None:
                frame = last_successful_frame.copy()
            else:
                time.sleep(0.1)
                continue
        else:
            last_successful_frame = frame.copy()
            consecutive_failures = 0
        
        frame_count += 1
        frame = cv2.flip(frame, 1)
        h, w, _ = frame.shape
        
        # Draw rectangle
        rect_color = (0, 255, 0)
        x_min, y_min, x_max, y_max = DETECTION_RECT
        top_left = (int(x_min * w), int(y_min * h))
        bottom_right = (int(x_max * w), int(y_max * h))
        cv2.rectangle(frame, top_left, bottom_right, rect_color, 3)
        
        # Process every frame for consistent detection
        raw_presence = "outside"
        image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = pose.process(image_rgb)

        if results.pose_landmarks:
            # Draw pose landmarks
            mp_drawing.draw_landmarks(
                frame, 
                results.pose_landmarks, 
                mp_pose.POSE_CONNECTIONS,
                mp_drawing.DrawingSpec(color=(245,117,66), thickness=2, circle_radius=2),
                mp_drawing.DrawingSpec(color=(245,66,230), thickness=2, circle_radius=2)
            )
            
            # Check if person is inside
            if is_person_in_rectangle(results.pose_landmarks, DETECTION_RECT):
                raw_presence = "inside"
                cv2.rectangle(frame, top_left, bottom_right, (0, 255, 255), 3)
        
        # Apply smoothing to prevent flickering
        presence_status = get_smoothed_presence(raw_presence)

        # Only emit if status actually changed
        if presence_status != current_presence_status:
            current_presence_status = presence_status
            socketio.emit('presence_status', {'status': presence_status})
            print(f"Presence status changed to: {presence_status}")
        
        with frame_lock:
            latest_frame = frame.copy()
        
        time.sleep(0.033)
    
    cap.release()

def gen_frames():
    global latest_frame
    
    while True:
        with frame_lock:
            if latest_frame is None:
                time.sleep(0.1)
                continue
            frame = latest_frame.copy()
        
        # Compress JPEG for faster streaming
        ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
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