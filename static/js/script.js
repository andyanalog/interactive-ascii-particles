const canvas = document.getElementById('particleCanvas');
const ctx = canvas.getContext('2d');
canvas.width = window.innerWidth;
canvas.height = window.innerHeight;

const socket = io();

const particlesArray = [];
const maxDistance = 200;
let handPositions = { x: canvas.width / 2, y: canvas.height / 2 };
let handStatus = "none";
let effectActive = false;

// Audio element
const audio = new Audio('/static/audio/audio.wav');
audio.loop = true;  // Loop the audio

socket.on('hand_positions', (data) => {
    handPositions.x = data.x * canvas.width;
    handPositions.y = data.y * canvas.height;
    handStatus = data.status;

    if (handStatus === 'two_open') {
        effectActive = true;
        if (audio.paused) {
            audio.play();  // Start playing the audio if it's paused
        }
    } else {
        effectActive = false;
        if (!audio.paused) {
            audio.pause();  // Stop the audio if it's playing
        }
    }
});

class Particle {
    constructor(x, y, size, color) {
        this.x = x;
        this.y = y;
        this.size = size;
        this.color = color;
        this.velocityX = Math.random() * 1 - 0.7;
        this.velocityY = Math.random() * 1 - 0.7;
        this.character = this.randomChar();
    }

    randomChar() {
        const chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*()";
        return chars.charAt(Math.floor(Math.random() * chars.length));
    }

    draw() {
        ctx.fillStyle = this.color;
        ctx.font = `${this.size}px monospace`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(this.character, this.x, this.y);
    }

    update() {
        let speedMultiplier = 1;

        if (handStatus === 'one_open') {
            speedMultiplier = 5; // Faster speed for one open hand
        } else if (handStatus === 'one_closed') {
            speedMultiplier = 0.2; // Slower speed for one closed hand
        } else if (handStatus === 'two_open') {
            speedMultiplier = 7; // Faster speed for two open hands
        }

        this.x += this.velocityX * speedMultiplier;
        this.y += this.velocityY * speedMultiplier;

        const dx = this.x - handPositions.x;
        const dy = this.y - handPositions.y;
        const distance = Math.sqrt(dx * dx + dy * dy);

        if (distance < maxDistance) {
            const forceDirectionX = dx / distance;
            const forceDirectionY = dy / distance;
            const force = (maxDistance - distance) / maxDistance;
            const directionX = forceDirectionX * force * this.size;
            const directionY = forceDirectionY * force * this.size;

            this.x += directionX;
            this.y += directionY;
        }

        if (this.x > canvas.width || this.x < 0) {
            this.velocityX = -this.velocityX;
        }

        if (this.y > canvas.height || this.y < 0) {
            this.velocityY = -this.velocityY;
        }

        // Change character randomly
        if (Math.random() < 0.02) {
            this.character = this.randomChar();
        }

        this.draw();
    }
}

function initParticles() {
    for (let i = 0; i < 400; i++) {
        const size = Math.random() * 20 + 10; // Larger size for characters
        const x = Math.random() * canvas.width;
        const y = Math.random() * canvas.height;
        particlesArray.push(new Particle(x, y, size, 'white'));
    }
}

function animate() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    if (effectActive) {
        ctx.globalCompositeOperation = 'lighter';
        ctx.fillStyle = `rgba(${Math.random()*255}, ${Math.random()*255}, ${Math.random()*255}, 0.5)`;
        ctx.fillRect(0, 0, canvas.width, canvas.height);
    } else {
        ctx.globalCompositeOperation = 'source-over';
    }

    particlesArray.forEach(particle => particle.update());
    requestAnimationFrame(animate);
}

window.addEventListener('resize', () => {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
});

initParticles();
animate();
