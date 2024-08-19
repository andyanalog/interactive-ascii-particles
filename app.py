from flask import Flask, render_template, Response
from flask_socketio import SocketIO, emit
import cv2
import mediapipe as mp
import numpy as np

app = Flask(__name__)
socketio = SocketIO(app)

mp_hands = mp.solutions.hands
hands = mp_hands.Hands(max_num_hands=2, min_detection_confidence=0.7, min_tracking_confidence=0.7)
mp_drawing = mp.solutions.drawing_utils

@app.route('/')
def index():
    return render_template('index.html')

def gen_frames():
    cap = cv2.VideoCapture(0)  # Capture from the first webcam

    while True:
        success, frame = cap.read()
        if not success:
            break
        else:
            image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = hands.process(image_rgb)

            hand_status = "none"
            hand_center = {"x": 0, "y": 0}
            open_hands_count = 0

            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    thumb_tip = hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP]
                    index_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
                    middle_tip = hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_TIP]
                    ring_tip = hand_landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_TIP]
                    pinky_tip = hand_landmarks.landmark[mp_hands.HandLandmark.PINKY_TIP]
                    wrist = hand_landmarks.landmark[mp_hands.HandLandmark.WRIST]

                    avg_finger_tip_y = (thumb_tip.y + index_tip.y + middle_tip.y + ring_tip.y + pinky_tip.y) / 5
                    wrist_y = wrist.y

                    if avg_finger_tip_y < wrist_y:  # open hand
                        open_hands_count += 1
                    else:  # closed hand
                        hand_status = "closed"

                    hand_center["x"] = (thumb_tip.x + index_tip.x + middle_tip.x + ring_tip.x + pinky_tip.x + wrist.x) / 6
                    hand_center["y"] = (thumb_tip.y + index_tip.y + middle_tip.y + ring_tip.y + pinky_tip.y + wrist.y) / 6

                    # Draw landmarks on the frame
                    mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

            if open_hands_count == 2:
                hand_status = "two_open"
            elif open_hands_count == 1:
                hand_status = "one_open"
            else:
                hand_status = "none"

            # Send hand data to client
            socketio.emit('hand_positions', {'x': hand_center['x'], 'y': hand_center['y'], 'status': hand_status})

            # Encode frame as JPEG
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    socketio.run(app, debug=True)
