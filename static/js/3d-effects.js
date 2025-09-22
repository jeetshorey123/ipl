// 3D Effects and Particle System for Cricket Analytics Hub

document.addEventListener('DOMContentLoaded', function() {
    // Initialize all 3D effects
    initParticleSystem();
    initFloatingShapes();
    init3DCardEffects();
    initMouseTracking();
    initScrollEffects();
    
    console.log('🚀 3D Cricket Analytics Hub loaded successfully!');
});

// Particle System
function initParticleSystem() {
    const particleSystem = document.getElementById('particleSystem');
    if (!particleSystem) return;
    
    const particleCount = 50;
    const colors = ['#00ffff', '#ff006e', '#8338ec', '#ffbe0b'];
    
    // Create particles
    for (let i = 0; i < particleCount; i++) {
        const particle = document.createElement('div');
        particle.className = 'particle';
        particle.style.left = Math.random() * 100 + '%';
        particle.style.animationDelay = Math.random() * 20 + 's';
        particle.style.animationDuration = (15 + Math.random() * 15) + 's';
        particle.style.background = colors[Math.floor(Math.random() * colors.length)];
        particle.style.boxShadow = `0 0 10px ${particle.style.background}`;
        
        // Random size variations
        const size = Math.random() * 4 + 2;
        particle.style.width = size + 'px';
        particle.style.height = size + 'px';
        
        particleSystem.appendChild(particle);
    }
}

// Floating Geometric Shapes
function initFloatingShapes() {
    const shapesContainer = document.getElementById('floatingShapes');
    if (!shapesContainer) return;
    
    const shapeCount = 30;
    const shapeTypes = ['triangle', 'square', 'circle', 'hexagon'];
    
    for (let i = 0; i < shapeCount; i++) {
        const shape = document.createElement('div');
        const shapeType = shapeTypes[Math.floor(Math.random() * shapeTypes.length)];
        
        shape.className = `shape ${shapeType}`;
        shape.style.left = Math.random() * 100 + '%';
        shape.style.animationDelay = Math.random() * 20 + 's';
        shape.style.animationDuration = (20 + Math.random() * 20) + 's';
        
        // Random positions and timing
        const startY = 100 + Math.random() * 20;
        shape.style.top = startY + 'vh';
        
        shapesContainer.appendChild(shape);
    }
}

// Enhanced 3D Card Effects
function init3DCardEffects() {
    const cards = document.querySelectorAll('.glass-card, .stat-card, .card');
    
    cards.forEach(card => {
        card.addEventListener('mouseenter', function(e) {
            // Add featured class for special effect
            this.classList.add('featured');
            
            // Create ripple effect
            createRipple(this, e);
        });
        
        card.addEventListener('mouseleave', function() {
            // Remove featured class
            setTimeout(() => {
                this.classList.remove('featured');
            }, 300);
        });
        
        card.addEventListener('mousemove', function(e) {
            // 3D tilt effect based on mouse position
            const rect = this.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            
            const centerX = rect.width / 2;
            const centerY = rect.height / 2;
            
            const rotateX = (y - centerY) / 10;
            const rotateY = (centerX - x) / 10;
            
            this.style.transform = `
                translateY(-15px) 
                rotateX(${rotateX}deg) 
                rotateY(${rotateY}deg) 
                scale(1.03)
            `;
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0) rotateX(0) rotateY(0) scale(1)';
        });
    });
}

// Create ripple effect on card interaction
function createRipple(element, event) {
    const ripple = document.createElement('div');
    const rect = element.getBoundingClientRect();
    const size = Math.max(rect.width, rect.height);
    const x = event.clientX - rect.left - size / 2;
    const y = event.clientY - rect.top - size / 2;
    
    ripple.style.cssText = `
        position: absolute;
        width: ${size}px;
        height: ${size}px;
        left: ${x}px;
        top: ${y}px;
        background: radial-gradient(circle, rgba(0, 255, 255, 0.3) 0%, transparent 70%);
        border-radius: 50%;
        transform: scale(0);
        animation: rippleEffect 0.6s ease-out;
        pointer-events: none;
        z-index: 1000;
    `;
    
    element.style.position = 'relative';
    element.appendChild(ripple);
    
    setTimeout(() => {
        ripple.remove();
    }, 600);
}

// Mouse tracking for enhanced interactivity
function initMouseTracking() {
    let mouseX = 0;
    let mouseY = 0;
    
    document.addEventListener('mousemove', function(e) {
        mouseX = e.clientX;
        mouseY = e.clientY;
        
        // Update CSS custom properties for mouse-based effects
        document.documentElement.style.setProperty('--mouse-x', mouseX + 'px');
        document.documentElement.style.setProperty('--mouse-y', mouseY + 'px');
        
        // Parallax effect for background elements
        const moveX = (mouseX - window.innerWidth / 2) * 0.01;
        const moveY = (mouseY - window.innerHeight / 2) * 0.01;
        
        const backgroundElements = document.querySelectorAll('.hero-section::before, .hero-section::after');
        backgroundElements.forEach(el => {
            if (el.style) {
                el.style.transform = `translate(${moveX}px, ${moveY}px)`;
            }
        });
    });
    
    // Enhanced button hover effects
    const buttons = document.querySelectorAll('.btn');
    buttons.forEach(button => {
        button.addEventListener('mouseenter', function() {
            // Add magnetic effect
            this.style.transition = 'transform 0.3s ease';
        });
        
        button.addEventListener('mousemove', function(e) {
            const rect = this.getBoundingClientRect();
            const x = e.clientX - rect.left - rect.width / 2;
            const y = e.clientY - rect.top - rect.height / 2;
            
            // Magnetic attraction effect
            this.style.transform = `
                translateY(-8px) 
                rotateX(10deg) 
                scale(1.05) 
                translate(${x * 0.1}px, ${y * 0.1}px)
            `;
        });
        
        button.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0) rotateX(0) scale(1) translate(0, 0)';
        });
    });
}

// Scroll-based animations and effects
function initScrollEffects() {
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -100px 0px'
    };
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.animationPlayState = 'running';
                entry.target.classList.add('animate-in');
            }
        });
    }, observerOptions);
    
    // Observe all cards and important elements
    const animatedElements = document.querySelectorAll('.glass-card, .stat-card, .btn, .chart-container');
    animatedElements.forEach(el => {
        observer.observe(el);
    });
    
    // Parallax scrolling for background elements
    window.addEventListener('scroll', function() {
        const scrolled = window.pageYOffset;
        const parallaxElements = document.querySelectorAll('.hero-section::before, .floating-shapes, .particle-system');
        
        parallaxElements.forEach(el => {
            if (el.style) {
                el.style.transform = `translateY(${scrolled * 0.5}px)`;
            }
        });
    });
}

// Add CSS for ripple animation
const rippleCSS = `
@keyframes rippleEffect {
    0% {
        transform: scale(0);
        opacity: 0.8;
    }
    100% {
        transform: scale(1);
        opacity: 0;
    }
}

.animate-in {
    animation: slideInUp 0.8s ease-out forwards;
}

@keyframes slideInUp {
    from {
        opacity: 0;
        transform: translateY(30px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

/* Enhanced glow effects */
.glass-card.featured {
    animation: cardGlow 2s ease-in-out infinite alternate;
}

@keyframes cardGlow {
    0% {
        box-shadow: 
            0 30px 60px rgba(0, 0, 0, 0.9),
            0 15px 30px rgba(0, 255, 255, 0.4),
            0 0 80px rgba(0, 255, 255, 0.3);
    }
    100% {
        box-shadow: 
            0 40px 80px rgba(0, 0, 0, 0.9),
            0 20px 40px rgba(255, 0, 110, 0.5),
            0 0 100px rgba(255, 0, 110, 0.4);
    }
}

/* Holographic text effect */
.text-hologram {
    background: linear-gradient(45deg, #00ffff, #ff006e, #8338ec, #ffbe0b);
    background-size: 400% 400%;
    background-clip: text;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    animation: hologramShift 3s ease infinite;
}

@keyframes hologramShift {
    0%, 100% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
}
`;

// Inject CSS
const styleSheet = document.createElement('style');
styleSheet.textContent = rippleCSS;
document.head.appendChild(styleSheet);

// Performance optimization
function optimizePerformance() {
    // Reduce animations on low-end devices
    if (navigator.hardwareConcurrency < 4) {
        document.documentElement.style.setProperty('--animation-duration', '10s');
        document.documentElement.style.setProperty('--particle-count', '20');
    }
    
    // Pause animations when tab is not visible
    document.addEventListener('visibilitychange', function() {
        const animations = document.querySelectorAll('.particle, .shape');
        animations.forEach(el => {
            el.style.animationPlayState = document.hidden ? 'paused' : 'running';
        });
    });
}

// Initialize performance optimizations
optimizePerformance();

// Export for global access
window.CricketAnalytics3D = {
    initParticleSystem,
    initFloatingShapes,
    init3DCardEffects,
    createRipple
};