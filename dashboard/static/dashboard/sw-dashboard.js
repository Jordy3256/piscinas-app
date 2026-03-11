/* dashboard/static/dashboard/sw-dashboard.js */

const VERSION = "v2026-03-11-10";
const CACHE = {
  static: `static-${VERSION}`,
  pages: `pages-${VERSION}`,
  images: `images-${VERSION}`,
};

const PRECACHE_URLS = [
  "/dashboard/offline/",
  "/dashboard/manifest.json",
  "/static/dashboard/icons/icon-192.png",
  "/static/dashboard/icons/icon-192-maskable.png",
  "/static/dashboard/icons/icon-512.png",
  "/static/dashboard/icons/icon-512-maskable.png",
];

function isSameOrigin(url) {
  try { return new URL(url).origin === self.location.origin; }
  catch { return false; }
}

function isHtml(request) {
  return request.mode === "navigate" || (request.headers.get("accept") || "").includes("text/html");
}

function isImage(request) {
  return request.destination === "image"
    || request.url.includes("/media/")
    || /\.(png|jpg|jpeg|gif|webp|svg)$/i.test(request.url);
}

function isStaticAsset(request) {
  return request.url.includes("/static/")
    || request.destination === "style"
    || request.destination === "script"
    || request.destination === "font";
}

function shouldBypassCache(request) {
  const url = new URL(request.url);
  if (url.pathname.startsWith("/admin/")) return true;
  if (url.pathname.startsWith("/logout/")) return true;
  if (url.pathname.startsWith("/login/")) return true;

  // CLAVE: no cachear páginas principales
  if (url.pathname === "/dashboard/") return true;
  if (url.pathname === "/dashboard/home/") return true;
  if (url.pathname === "/dashboard/panel/") return true;

  return false;
}

async function safePut(cacheName, request, response) {
  try {
    if (!isSameOrigin(request.url)) return;
    if (!response || response.status !== 200) return;
    const cache = await caches.open(cacheName);
    await cache.put(request, response.clone());
  } catch (e) {
    console.warn("[SW] safePut error:", e);
  }
}

async function cacheFirst(request, cacheName) {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(request);
  if (cached) return cached;

  const fresh = await fetch(request, { cache: "no-store" });
  await safePut(cacheName, request, fresh);
  return fresh;
}

async function networkOnlyHtml(request) {
  try {
    return await fetch(request, { cache: "no-store" });
  } catch (e) {
    const cache = await caches.open(CACHE.static);
    const offline = await cache.match("/dashboard/offline/");
    return offline || new Response("Offline", { status: 503 });
  }
}

async function networkFirst(request, cacheName) {
  const cache = await caches.open(cacheName);

  try {
    const fresh = await fetch(request, { cache: "no-store" });
    await safePut(cacheName, request, fresh);
    return fresh;
  } catch (e) {
    const cached = await cache.match(request);
    if (cached) return cached;

    if (isHtml(request)) {
      const off = await caches.open(CACHE.static).then(c => c.match("/dashboard/offline/"));
      if (off) return off;
    }

    throw e;
  }
}

async function precacheAll(cache, urls) {
  for (const u of urls) {
    try {
      const req = new Request(u, { cache: "reload" });
      const res = await fetch(req);
      if (res.status === 200) {
        await cache.put(req, res);
      }
    } catch (e) {
      console.warn("[SW] precache fail:", u, e);
    }
  }
}

self.addEventListener("install", (event) => {
  event.waitUntil((async () => {
    const cache = await caches.open(CACHE.static);
    await precacheAll(cache, PRECACHE_URLS);
    await self.skipWaiting();
  })());
});

self.addEventListener("activate", (event) => {
  event.waitUntil((async () => {
    const keys = await caches.keys();
    const allow = new Set([CACHE.static, CACHE.pages, CACHE.images]);
    await Promise.all(keys.map((k) => (!allow.has(k) ? caches.delete(k) : null)));
    await self.clients.claim();
  })());
});

self.addEventListener("message", (event) => {
  if (event.data === "SKIP_WAITING") {
    self.skipWaiting();
  }
});

self.addEventListener("push", (event) => {
  let data = {};
  try {
    data = event.data ? event.data.json() : {};
  } catch (e) {
    data = { title: "Piscinas App", body: event.data ? event.data.text() : "Nueva notificación" };
  }

  const title = data.title || "Piscinas App";
  const body = data.body || data.message || "Tienes una nueva notificación.";
  const url = data.url || "/dashboard/home/";
  const tag = (data.tag && String(data.tag).trim()) ? String(data.tag).trim() : ("piscinas-" + Date.now());

  const options = {
    body,
    icon: data.icon || "/static/dashboard/icons/icon-192.png",
    badge: data.badge || "/static/dashboard/icons/icon-192.png",
    data: { url },
    tag,
    renotify: true,
  };

  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();

  const url = (event.notification?.data?.url) || "/dashboard/home/";

  event.waitUntil(
    (async () => {
      const allClients = await clients.matchAll({ type: "window", includeUncontrolled: true });
      for (const client of allClients) {
        if (client.url.includes("/dashboard/") && "focus" in client) {
          return client.focus();
        }
      }
      if (clients.openWindow) return clients.openWindow(url);
    })()
  );
});

self.addEventListener("fetch", (event) => {
  const req = event.request;

  if (req.method !== "GET") return;
  if (!isSameOrigin(req.url)) return;

  if (shouldBypassCache(req)) {
    if (isHtml(req)) {
      event.respondWith(networkOnlyHtml(req));
      return;
    }
    return;
  }

  if (isHtml(req)) {
    event.respondWith(networkFirst(req, CACHE.pages));
    return;
  }

  if (isImage(req)) {
    event.respondWith(cacheFirst(req, CACHE.images));
    return;
  }

  if (isStaticAsset(req)) {
    event.respondWith(cacheFirst(req, CACHE.static));
    return;
  }

  event.respondWith(networkFirst(req, CACHE.pages));
});