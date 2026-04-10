/**
 * Infinite Scroll for Image Feed
 * Lazily loads more images as user scrolls to bottom
 */
(function() {
    'use strict';

    const state = {
        loading: false,
        hasMore: true,
        nextPage: null,
        feedUrl: window.FEED_URL || window.location.pathname,
        container: null,
        trigger: null,
        loadingIndicator: null,
        observer: null
    };

    function init() {
        state.container = document.getElementById('images-container');
        state.trigger = document.getElementById('load-more-trigger');
        state.loadingIndicator = document.getElementById('loading-indicator');

        if (!state.container || !state.trigger) {
            return;
        }

        state.nextPage = state.trigger.dataset.nextPage;
        state.hasMore = !!state.nextPage;

        // Use Intersection Observer for efficient scroll detection
        state.observer = new IntersectionObserver(handleIntersection, {
            root: null,
            rootMargin: '100px',
            threshold: 0.1
        });

        state.observer.observe(state.trigger);
    }

    function handleIntersection(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting && state.hasMore && !state.loading) {
                loadMore();
            }
        });
    }

    async function loadMore() {
        if (state.loading || !state.hasMore) return;

        state.loading = true;
        showLoading(true);

        try {
            const url = new URL(state.feedUrl, window.location.origin);
            url.searchParams.set('page', state.nextPage);

            const response = await fetch(url, {
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });

            if (!response.ok) {
                throw new Error('Network response was not ok');
            }

            const data = await response.json();

            if (data.html && data.html.trim()) {
                // Append new content
                state.container.insertAdjacentHTML('beforeend', data.html);

                // Reinitialize like buttons for new content
                if (typeof initializeLikeButtons === 'function') {
                    initializeLikeButtons();
                }
            }

            state.hasMore = data.has_next;
            state.nextPage = data.next_page;

            // Update trigger element
            if (state.hasMore) {
                state.trigger.dataset.nextPage = state.nextPage;
            } else {
                // No more content, remove trigger and observer
                state.observer.disconnect();
                state.trigger.remove();
                if (state.loadingIndicator) {
                    state.loadingIndicator.remove();
                }
            }
        } catch (error) {
            console.error('Error loading more images:', error);
            state.hasMore = false;
        } finally {
            state.loading = false;
            showLoading(false);
        }
    }

    function showLoading(show) {
        if (state.loadingIndicator) {
            state.loadingIndicator.classList.toggle('hidden', !show);
        }
    }

    // Initialize on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // Expose for external use
    window.InfiniteScroll = {
        refresh: init,
        loadMore: loadMore
    };
})();
