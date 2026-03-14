importScripts('https://cdn.onesignal.com/sdks/OneSignalSDKWorker.js');

console.log('Service Worker cargado correctamente');

const staticCacheName = "clustertim-pwa-v" + new Date().getTime();
const filesToCache = [
    '/',
    '/static/images/icons/icon-192x192.png',
    '/static/images/icons/icon-512x512.png',
    '/static/images/icons/icon-180x180.png'
];

self.addEventListener('install', event => {
    console.log('SW: Instalando...');
    self.skipWaiting();
    event.waitUntil(
        caches.open(staticCacheName)
            .then(cache => {
                console.log('SW: Cache abierto');
                return cache.addAll(filesToCache);
            })
            .then(() => {
                console.log('SW: Archivos cacheados correctamente');
            })
            .catch(err => {
                console.error('SW: Error cacheando archivos:', err);
            })
    );
});

self.addEventListener('activate', event => {
    console.log('SW: Activando...');
    event.waitUntil(
        caches.keys().then(cacheNames => {
            return Promise.all(
                cacheNames
                    .filter(name => name.startsWith("clustertim-pwa-"))
                    .filter(name => name !== staticCacheName)
                    .map(name => caches.delete(name))
            );
        }).then(() => self.clients.claim())
    );
});

self.addEventListener('fetch', event => {
    if (event.request.mode === 'navigate') {
        console.log('SW: Navegación detectada, cargando desde la red:', event.request.url);
        event.respondWith(
            fetch(event.request)
                .then(response => {
                    return response;
                })
                .catch(() => {
                    return caches.match('/'); // fallback offline
                })
        );
        return;
    }

    event.respondWith(
        caches.match(event.request)
            .then(response => {
                return response || fetch(event.request);
            })
    );
});