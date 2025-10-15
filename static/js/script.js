const socket = io();

let currentImageIndex = 0;
const totalImages = 10;
let handStatus = "none";
let intervalId = null;
const changeInterval = 500; // 0.5 seconds between image changes

const imageElement = document.getElementById('mainImage');

// Connection status
socket.on('connect', () => {
    console.log('Connected to server');
});

socket.on('disconnect', () => {
    console.log('Disconnected from server');
});

socket.on('hand_status', (data) => {
    console.log('Received hand status:', data.status);
    const previousStatus = handStatus;
    handStatus = data.status;
    
    // If status changed, handle the interval
    if (previousStatus !== handStatus) {
        // Clear any existing interval
        if (intervalId) {
            clearInterval(intervalId);
            intervalId = null;
        }
        
        if (handStatus === 'open') {
            // Start moving forward continuously
            console.log('Starting forward movement');
            intervalId = setInterval(() => {
                if (currentImageIndex < totalImages - 1) {
                    currentImageIndex++;
                    updateImage();
                    console.log('Moving forward to image:', currentImageIndex);
                } else {
                    console.log('Reached last image, stopping');
                    clearInterval(intervalId);
                    intervalId = null;
                }
            }, changeInterval);
        } else if (handStatus === 'closed') {
            // Start moving backward continuously
            console.log('Starting backward movement');
            intervalId = setInterval(() => {
                if (currentImageIndex > 0) {
                    currentImageIndex--;
                    updateImage();
                    console.log('Moving backward to image:', currentImageIndex);
                } else {
                    console.log('Reached first image, stopping');
                    clearInterval(intervalId);
                    intervalId = null;
                }
            }, changeInterval);
        }
    }
});

function updateImage() {
    imageElement.src = `/static/images/${currentImageIndex}.jpg`;
    document.getElementById('imageCounter').textContent = `Image ${currentImageIndex + 1} of ${totalImages}`;
}

// Initialize with first image
updateImage();