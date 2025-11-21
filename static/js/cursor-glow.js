// Cursor glow effect
class CursorGlow {
    constructor() {
        this.cursor = null;
        this.cursorGlow = null;
        this.init();
    }
    
    init() {
        // Create cursor elements
        this.cursor = document.createElement('div');
        this.cursor.id = 'cursor';
        document.body.appendChild(this.cursor);
        
        this.cursorGlow = document.createElement('div');
        this.cursorGlow.id = 'cursor-glow';
        document.body.appendChild(this.cursorGlow);
        
        // Track mouse movement
        document.addEventListener('mousemove', (e) => {
            this.moveCursor(e.clientX, e.clientY);
        });
        
        // Hide cursor when leaving window
        document.addEventListener('mouseleave', () => {
            this.cursor.style.opacity = '0';
            this.cursorGlow.style.opacity = '0';
        });
        
        document.addEventListener('mouseenter', () => {
            this.cursor.style.opacity = '1';
            this.cursorGlow.style.opacity = '1';
        });
    }
    
    moveCursor(x, y) {
        // Update cursor position
        this.cursor.style.left = `${x}px`;
        this.cursor.style.top = `${y}px`;
        this.cursor.style.transform = 'translate(-50%, -50%)';
        
        // Update glow position (offset to center it)
        this.cursorGlow.style.left = `${x}px`;
        this.cursorGlow.style.top = `${y}px`;
        this.cursorGlow.style.transform = 'translate(-50%, -50%)';
    }
}

// Initialize cursor glow
document.addEventListener('DOMContentLoaded', () => {
    // Only initialize on non-touch devices
    if (!('ontouchstart' in window)) {
        new CursorGlow();
    }
});

// Helper function to add fade-in animation to elements
function addFadeInAnimation() {
    const elements = document.querySelectorAll('.card, .stat-card, h1, h2');
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach((entry, index) => {
            if (entry.isIntersecting) {
                setTimeout(() => {
                    entry.target.classList.add('fade-in');
                }, index * 100);
                observer.unobserve(entry.target);
            }
        });
    }, {
        threshold: 0.1
    });
    
    elements.forEach(element => {
        observer.observe(element);
    });
}

// Initialize animations on page load
document.addEventListener('DOMContentLoaded', addFadeInAnimation);
