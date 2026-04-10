/**
 * Allows users to select and bookmark images from a webpage.
 */

(function() {
    const SITE_URL = window.IMAGEMARK_SITE_URL || 'http://127.0.0.1:8000';
    const MIN_IMAGE_SIZE = 100;
    
    if (window.imageMarkBookmarklet) {
        window.imageMarkBookmarklet.open();
        return;
    }

    function isValidImageUrl(url) {
        if (!url) return false;
        const validExtensions = ['jpg', 'jpeg', 'png', 'gif', 'webp'];
        try {
            const urlObj = new URL(url, window.location.href);
            const path = urlObj.pathname.toLowerCase();
            return validExtensions.some(ext => path.endsWith('.' + ext));
        } catch {
            return false;
        }
    }

    function getAbsoluteUrl(url) {
        if (!url) return null;
        try {
            return new URL(url, window.location.href).href;
        } catch {
            return null;
        }
    }

    function extractImages() {
        const images = new Map();
        
        document.querySelectorAll('img').forEach(img => {
            const src = img.src || img.dataset.src || img.dataset.lazySrc;
            const absoluteUrl = getAbsoluteUrl(src);
            
            if (absoluteUrl && isValidImageUrl(absoluteUrl)) {
                const width = img.naturalWidth || img.width || 0;
                const height = img.naturalHeight || img.height || 0;
                
                if (width >= MIN_IMAGE_SIZE || height >= MIN_IMAGE_SIZE || (!width && !height)) {
                    if (!images.has(absoluteUrl)) {
                        images.set(absoluteUrl, {
                            url: absoluteUrl,
                            width: width,
                            height: height,
                            alt: img.alt || ''
                        });
                    }
                }
            }
        });
        
        document.querySelectorAll('*').forEach(el => {
            const style = getComputedStyle(el);
            const bgImage = style.backgroundImage;
            
            if (bgImage && bgImage !== 'none') {
                const match = bgImage.match(/url\(['"]?([^'"]+)['"]?\)/);
                if (match) {
                    const absoluteUrl = getAbsoluteUrl(match[1]);
                    if (absoluteUrl && isValidImageUrl(absoluteUrl) && !images.has(absoluteUrl)) {
                        images.set(absoluteUrl, {
                            url: absoluteUrl,
                            width: 0,
                            height: 0,
                            alt: ''
                        });
                    }
                }
            }
        });
        
        document.querySelectorAll('[srcset]').forEach(el => {
            const srcset = el.getAttribute('srcset');
            const sources = srcset.split(',').map(s => s.trim().split(/\s+/)[0]);
            
            sources.forEach(src => {
                const absoluteUrl = getAbsoluteUrl(src);
                if (absoluteUrl && isValidImageUrl(absoluteUrl) && !images.has(absoluteUrl)) {
                    images.set(absoluteUrl, {
                        url: absoluteUrl,
                        width: 0,
                        height: 0,
                        alt: ''
                    });
                }
            });
        });
        
        document.querySelectorAll('picture source').forEach(source => {
            const srcset = source.getAttribute('srcset');
            if (srcset) {
                const sources = srcset.split(',').map(s => s.trim().split(/\s+/)[0]);
                sources.forEach(src => {
                    const absoluteUrl = getAbsoluteUrl(src);
                    if (absoluteUrl && isValidImageUrl(absoluteUrl) && !images.has(absoluteUrl)) {
                        images.set(absoluteUrl, {
                            url: absoluteUrl,
                            width: 0,
                            height: 0,
                            alt: ''
                        });
                    }
                });
            }
        });
        
        document.querySelectorAll('meta[property="og:image"], meta[name="twitter:image"]').forEach(meta => {
            const content = meta.getAttribute('content');
            const absoluteUrl = getAbsoluteUrl(content);
            if (absoluteUrl && isValidImageUrl(absoluteUrl) && !images.has(absoluteUrl)) {
                images.set(absoluteUrl, {
                    url: absoluteUrl,
                    width: 0,
                    height: 0,
                    alt: 'Social media image'
                });
            }
        });
        
        return Array.from(images.values());
    }

    function loadStyles() {
        const link = document.createElement('link');
        link.id = 'imagemark-styles';
        link.rel = 'stylesheet';
        link.href = `${SITE_URL}/static/css/bookmarklet.css`;
        document.head.appendChild(link);
    }

    function createUI() {
        loadStyles();
        
        const overlay = document.createElement('div');
        overlay.className = 'imagemark-overlay';
        overlay.id = 'imagemark-overlay';
        
        overlay.innerHTML = `
            <div class="imagemark-container">
                <div class="imagemark-header">
                    <div class="imagemark-logo">
                        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v16z" stroke="#14b8a6" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                            <circle cx="12" cy="10" r="3" stroke="#14b8a6" stroke-width="2"/>
                        </svg>
                        <span>ImageMark</span>
                    </div>
                    <button class="imagemark-close" id="imagemark-close">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M18 6L6 18M6 6l12 12"/>
                        </svg>
                    </button>
                </div>
                
                <div id="imagemark-content">
                    <div class="imagemark-loading">
                        <div class="imagemark-spinner"></div>
                        <p>Scanning page for images...</p>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(overlay);
        
        document.getElementById('imagemark-close').addEventListener('click', close);
        
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) {
                close();
            }
        });
        
        document.addEventListener('keydown', handleKeydown);
        
        return overlay;
    }

    function handleKeydown(e) {
        if (e.key === 'Escape') {
            close();
        }
    }

    function renderImages(images) {
        const content = document.getElementById('imagemark-content');
        
        if (images.length === 0) {
            content.innerHTML = `
                <div class="imagemark-empty">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                        <rect x="3" y="3" width="18" height="18" rx="2"/>
                        <circle cx="8.5" cy="8.5" r="1.5"/>
                        <path d="M21 15l-5-5L5 21"/>
                    </svg>
                    <h3>No Images Found</h3>
                    <p>We couldn't find any bookmarkable images on this page.</p>
                </div>
            `;
            return;
        }
        
        const largeImages = images.filter(img => img.width >= 500 || img.height >= 500);
        const mediumImages = images.filter(img => (img.width >= 200 || img.height >= 200) && img.width < 500 && img.height < 500);
        
        content.innerHTML = `
            <p class="imagemark-info">
                Found <span class="imagemark-count">${images.length}</span> images on this page. 
                Click an image to bookmark it.
            </p>
            
            <div class="imagemark-filter">
                <button class="imagemark-filter-btn active" data-filter="all">All (${images.length})</button>
                ${largeImages.length > 0 ? `<button class="imagemark-filter-btn" data-filter="large">Large (${largeImages.length})</button>` : ''}
                ${mediumImages.length > 0 ? `<button class="imagemark-filter-btn" data-filter="medium">Medium (${mediumImages.length})</button>` : ''}
                <input type="text" class="imagemark-search" placeholder="Filter by URL or alt text..." id="imagemark-search">
            </div>
            
            <div class="imagemark-grid" id="imagemark-grid"></div>
        `;
        
        const grid = document.getElementById('imagemark-grid');
        let currentFilter = 'all';
        let searchQuery = '';
        
        function renderGrid() {
            let filtered = images;
            
            if (currentFilter === 'large') {
                filtered = filtered.filter(img => img.width >= 500 || img.height >= 500);
            } else if (currentFilter === 'medium') {
                filtered = filtered.filter(img => (img.width >= 200 || img.height >= 200) && img.width < 500 && img.height < 500);
            }
            
            if (searchQuery) {
                const query = searchQuery.toLowerCase();
                filtered = filtered.filter(img => 
                    img.url.toLowerCase().includes(query) || 
                    img.alt.toLowerCase().includes(query)
                );
            }
            
            grid.innerHTML = filtered.map(img => `
                <div class="imagemark-item" data-url="${encodeURIComponent(img.url)}">
                    <img src="${img.url}" alt="${img.alt}" loading="lazy" onerror="this.parentElement.style.display='none'">
                    ${img.width && img.height ? `<span class="imagemark-item-size">${img.width}×${img.height}</span>` : ''}
                    <div class="imagemark-item-overlay">
                        <button class="imagemark-item-btn">Bookmark This</button>
                    </div>
                </div>
            `).join('');
            
            grid.querySelectorAll('.imagemark-item').forEach(item => {
                item.addEventListener('click', () => {
                    const url = decodeURIComponent(item.dataset.url);
                    bookmarkImage(url);
                });
            });
        }
        
        content.querySelectorAll('.imagemark-filter-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                content.querySelectorAll('.imagemark-filter-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                currentFilter = btn.dataset.filter;
                renderGrid();
            });
        });
        
        document.getElementById('imagemark-search').addEventListener('input', (e) => {
            searchQuery = e.target.value;
            renderGrid();
        });
        
        renderGrid();
    }

    function bookmarkImage(imageUrl) {
        const title = document.title || 'Untitled Image';
        const createUrl = `${SITE_URL}/images/create/?url=${encodeURIComponent(imageUrl)}&title=${encodeURIComponent(title)}`;
        window.open(createUrl, '_blank');
    }

    function close() {
        const overlay = document.getElementById('imagemark-overlay');
        const styles = document.getElementById('imagemark-styles');
        
        if (overlay) overlay.remove();
        if (styles) styles.remove();
        
        document.removeEventListener('keydown', handleKeydown);
        window.imageMarkBookmarklet = null;
    }

    function open() {
        const existing = document.getElementById('imagemark-overlay');
        if (existing) {
            existing.style.display = 'block';
            return;
        }
        
        createUI();
        
        setTimeout(() => {
            const images = extractImages();
            renderImages(images);
        }, 100);
    }

    window.imageMarkBookmarklet = { open, close };
    open();
})();
