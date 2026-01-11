// sw.js - Service Worker for Beit Din Gadol
// This service worker caches the site's core assets so that subsequent visits
// load more quickly and the site is available offline. It uses a simple
// cache-first strategy: it tries to serve cached files and falls back to
// the network when necessary, caching new responses on the fly.

const CACHE_NAME = 'bdg-cache-v1';
const URLS_TO_CACHE = [
  // Cache the root and major pages
  './',
  './index.html',
  './qa.html',
  // Cache scripts and workers
  './script.js',
  './worker.js',
  './sw.js',
  // Cache styles
  './styles.css',
  // Cache data files (may be large on first fetch)
  './responsa.json'
];

// Install event: pre-cache core assets
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => {
      return cache.addAll(URLS_TO_CACHE);
    })
  );
});

// Activate event: clean up old caches if necessary
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keyList => {
      return Promise.all(
        keyList.map(key => {
          if (key !== CACHE_NAME) {
            return caches.delete(key);
          }
        })
      );
    })
  );
});

// Fetch event: respond with cached resources when available, otherwise fetch from network
self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request).then(cachedResponse => {
      // Return cached response if found
      if (cachedResponse) {
        return cachedResponse;
      }
      // Else fetch from network and cache the result for next time
      return fetch(event.request)
        .then(response => {
          // Only cache successful responses (status 200) and same-origin requests
          if (!response || response.status !== 200 || response.type !== 'basic') {
            return response;
          }
          const responseToCache = response.clone();
          caches.open(CACHE_NAME).then(cache => {
            cache.put(event.request, responseToCache);
          });
          return response;
        })
        .catch(() => {
          // Optionally, return a fallback page or asset here
          return cachedResponse;
        });
    })
  );
});