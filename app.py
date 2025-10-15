from flask import Flask, render_template, Response
from flask_socketio import SocketIO, emit
import cv2
import mediapipe as mp
import numpy as np
import threading
import time

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

mp_hands = mp.solutions.hands
hands = mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.7, min_tracking_confidence=0.7)
mp_drawing = mp.solutions.drawing_utils

# Global variables
current_hand_status = "none"
latest_frame = None
frame_lock = threading.Lock()
camera_active = True

@app.route('/')
def index():
    return render_template('index.html')

def camera_loop():
    """Single camera capture loop that handles both detection and video feed"""
    global current_hand_status, latest_frame, camera_active
    
    cap = cv2.VideoCapture(0)
    
    while camera_active:
        success, frame = cap.read()
        if not success:
            time.sleep(0.1)
            continue
            
        # Process frame for hand detection
        image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(image_rgb)

        hand_status = "none"

        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                # Get finger tips and wrist
                thumb_tip = hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP]
                index_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
                middle_tip = hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_TIP]
                ring_tip = hand_landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_TIP]
                pinky_tip = hand_landmarks.landmark[mp_hands.HandLandmark.PINKY_TIP]
                wrist = hand_landmarks.landmark[mp_hands.HandLandmark.WRIST]

                # Calculate average finger tip position
                avg_finger_tip_y = (thumb_tip.y + index_tip.y + middle_tip.y + ring_tip.y + pinky_tip.y) / 5
                wrist_y = wrist.y

                # Determine if hand is open or closed
                if avg_finger_tip_y < wrist_y:
                    hand_status = "open"
                else:
                    hand_status = "closed"
                
                # Draw landmarks on the frame
                mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

        # Only emit if status changed
        if hand_status != current_hand_status:
            current_hand_status = hand_status
            socketio.emit('hand_status', {'status': hand_status})
            print(f"Hand status: {hand_status}")
        
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
    emit('hand_status', {'status': current_hand_status})

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