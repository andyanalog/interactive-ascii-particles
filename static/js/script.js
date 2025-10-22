const socket = io();

let currentImageIndex = 0;
const totalImages = 10;
let presenceStatus = "outside";
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

socket.on('presence_status', (data) => {
    console.log('Received presence status:', data.status);
    const previousStatus = presenceStatus;
    presenceStatus = data.status;
    
    // If status changed, handle the interval
    if (previousStatus !== presenceStatus) {
        // Clear any existing interval
        if (intervalId) {
            clearInterval(intervalId);
            intervalId = null;
        }
        
        if (presenceStatus === 'inside') {
            // Start moving forward continuously and loop
            console.log('Person detected inside - starting forward playback');
            intervalId = setInterval(() => {
                currentImageIndex++;
                if (currentImageIndex >= totalImages) {
                    currentImageIndex = 0; // Loop back to start
                    console.log('Reached last image, looping to start');
                }
                updateImage();
                console.log('Playing forward: image', currentImageIndex);
            }, changeInterval);
        } else if (presenceStatus === 'outside') {
            // Start moving backward to frame 0 and stop
            console.log('Person left rectangle - rewinding to frame 0');
            if (currentImageIndex > 0) {
                intervalId = setInterval(() => {
                    currentImageIndex--;
                    updateImage();
                    console.log('Rewinding: image', currentImageIndex);
                    
                    if (currentImageIndex === 0) {
                        console.log('Reached frame 0, stopping playback');
                        clearInterval(intervalId);
                        intervalId = null;
                    }
                }, changeInterval);
            }
        }
    }
});

function updateImage() {
    imageElement.src = `/static/images/${currentImageIndex}.jpg`;
    document.getElementById('imageCounter').textContent = `Image ${currentImageIndex + 1} of ${totalImages}`;
}

// Initialize with first image
updateImage();