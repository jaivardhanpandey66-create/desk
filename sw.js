const C = "desk-v1";
self.addEventListener("install", e => { e.waitUntil(caches.open(C).then(c => c.addAll(["/", "/desk_ui.html", "/manifest.json"])).then(() => self.skipWaiting())); });
self.addEventListener("fetch", e => { e.respondWith(caches.match(e.request).then(r => r || fetch(e.request).catch(() => caches.match("/")))); });