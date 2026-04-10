/**
 * Image Like/Unlike functionality
 * Handles AJAX-based like toggling for images
 */

document.addEventListener('DOMContentLoaded', function() {
    initializeLikeButtons();
});

/**
 * Initialize all like buttons on the page
 * Call this after dynamically adding new content
 */
function initializeLikeButtons() {
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
    
    if (!csrfToken) {
        console.warn('CSRF token not found. Like functionality may not work.');
        return;
    }

    document.querySelectorAll('.like-button:not([data-initialized])').forEach(button => {
        button.setAttribute('data-initialized', 'true');
        
        button.addEventListener('click', async function(e) {
            e.preventDefault();
            
            const imageId = this.dataset.id;
            if (!imageId) return;
            
            const icon = this.querySelector('.like-icon');
            const countSpan = this.querySelector('.like-count');
            
            // Disable button during request
            this.disabled = true;
            
            try {
                const response = await fetch(window.LIKE_URL || '/images/like/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded',
                        'X-CSRFToken': csrfToken
                    },
                    body: `id=${imageId}`
                });

                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }

                const data = await response.json();

                if (data.status === 'ok') {
                    // Update icon
                    if (icon) {
                        icon.textContent = data.liked ? 'favorite' : 'favorite_border';
                    }
                    
                    // Update button styling
                    if (data.liked) {
                        this.classList.add('text-red-500');
                    } else {
                        this.classList.remove('text-red-500');
                    }
                    
                    // Update count
                    if (countSpan) {
                        countSpan.textContent = data.total_likes;
                    }
                    
                    // Dispatch custom event for other scripts to listen to
                    this.dispatchEvent(new CustomEvent('like-toggled', {
                        bubbles: true,
                        detail: {
                            imageId: imageId,
                            liked: data.liked,
                            totalLikes: data.total_likes
                        }
                    }));
                }
            } catch (error) {
                console.error('Error toggling like:', error);
            } finally {
                this.disabled = false;
            }
        });
    });
}

// Export for use in other scripts
window.initializeLikeButtons = initializeLikeButtons;
