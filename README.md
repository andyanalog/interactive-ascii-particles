# Interactive ASCII Particles

This project is a web-based interactive art application that uses real-time hand detection and ASCII particles to create dynamic visual effects. It is built using Flask, SocketIO, and MediaPipe for hand tracking, combined with HTML5 Canvas for rendering the visual effects.

## Features

- **Interactive ASCII Particles**: Particles represented by random ASCII characters move and change based on hand gestures detected by MediaPipe.
- **Hand Tracking**: Real-time hand detection using MediaPipe. Different effects are applied based on hand gestures:
  - **One Open Hand**: Particles move faster.
  - **One Closed Hand**: Particles move slower.
  - **Two Open Hands**: Activate visual and audio effects.
- **Webcam Feed**: Display a live feed from the webcam with the detected hand landmarks.

## Installation

1. **Clone the repository**:

   ```bash
   git clone https://github.com/andyanalog/interactive-ascii-particles.git
   cd interactive-ascii-particles

2. **Install the required packages:**:

   ```bash
   pip install -r requirements.txt

## Usage

1. **Run the Flask application**:

   ```bash
   python app.py

2. **Run the Flask application**:

   Open your web browser and navigate to http://localhost:5000 to view the interactive application.

## Files

- **app.py**: The Flask application that handles video feed, hand detection, and serves the HTML.
- **index.html**: The front-end HTML and JavaScript for rendering the interactive particles and webcam feed.

## Dependencies

- Flask
- Flask-SocketIO
- OpenCV
- MediaPipe
- NumPy

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
