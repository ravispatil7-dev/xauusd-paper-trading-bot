const CACHE_NAME = 'goldbot-v1';
const STATIC_ASSETS = [
    '/',
    '/index.html',
    '/app.js',
    '/manifest.json',
    'https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js',
    'https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns@3.0.0/dist/chartjs-adapter-date-fns.bundle.min.js',
    'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css'
];

// Install event - cache static assets
self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then((cache) => {
                console.log('[SW] Caching static assets');
                return cache.addAll(STATIC_ASSETS);
            })
            .catch((err) => {
                console.log('[SW] Cache failed:', err);
            })
    );
    self.skipWaiting();
});

// Activate event - clean old caches
self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames
                    .filter((name) => name !== CACHE_NAME)
                    .map((name) => caches.delete(name))
            );
        })
    );
    self.clients.claim();
});

// Fetch event - network-first strategy for API, cache-first for static
self.addEventListener('fetch', (event) => {
    const { request } = event;
    const url = new URL(request.url);

    // API requests - network first, fallback to cache
    if (url.pathname.startsWith('/api/') || url.pathname === '/ws') {
        event.respondWith(
            fetch(request)
                .then((response) => {
                    // Clone and cache successful responses
                    if (response.ok) {
                        const clone = response.clone();
                        caches.open(CACHE_NAME).then((cache) => {
                            cache.put(request, clone);
                        });
                    }
                    return response;
                })
                .catch(() => {
                    return caches.match(request);
                })
        );
        return;
    }

    // Static assets - cache first, fallback to network
    event.respondWith(
        caches.match(request).then((cached) => {
            if (cached) {
                return cached;
            }
            return fetch(request).then((response) => {
                if (response.ok) {
                    const clone = response.clone();
                    caches.open(CACHE_NAME).then((cache) => {
                        cache.put(request, clone);
                    });
                }
                return response;
            });
        })
    );
});

// Background sync for trades when offline
self.addEventListener('sync', (event) => {
    if (event.tag === 'sync-trades') {
        event.waitUntil(syncPendingTrades());
    }
});

async function syncPendingTrades() {
    const pending = await getPendingTrades();
    for (const trade of pending) {
        try {
            await fetch('/api/trade/open', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(trade)
            });
            await removePendingTrade(trade.id);
        } catch (err) {
            console.log('[SW] Failed to sync trade:', err);
        }
    }
}

// Push notifications for signals
self.addEventListener('push', (event) => {
    const data = event.data ? event.data.json() : {};
    const options = {
        body: data.message || 'New trading signal available!',
        icon: '/icon-192x192.png',
        badge: '/icon-72x72.png',
        tag: 'goldbot-signal',
        requireInteraction: true,
        actions: [
            { action: 'open', title: 'Open App' },
            { action: 'dismiss', title: 'Dismiss' }
        ]
    };
    event.waitUntil(
        self.registration.showNotification('GoldBot Signal', options)
    );
});

self.addEventListener('notificationclick', (event) => {
    event.notification.close();
    if (event.action === 'open' || !event.action) {
        event.waitUntil(
            clients.openWindow('/')
        );
    }
});

// Helper functions for IndexedDB
function getPendingTrades() {
    return new Promise((resolve) => {
        const request = indexedDB.open('GoldBotDB', 1);
        request.onsuccess = (event) => {
            const db = event.target.result;
            const tx = db.transaction('pendingTrades', 'readonly');
            const store = tx.objectStore('pendingTrades');
            const getAll = store.getAll();
            getAll.onsuccess = () => resolve(getAll.result);
            getAll.onerror = () => resolve([]);
        };
        request.onerror = () => resolve([]);
    });
}

function removePendingTrade(id) {
    return new Promise((resolve) => {
        const request = indexedDB.open('GoldBotDB', 1);
        request.onsuccess = (event) => {
            const db = event.target.result;
            const tx = db.transaction('pendingTrades', 'readwrite');
            const store = tx.objectStore('pendingTrades');
            store.delete(id);
            tx.oncomplete = () => resolve();
        };
    });
}
