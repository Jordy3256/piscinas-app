/* dashboard/static/dashboard/sw-dashboard.js */

const VERSION = "v2026-10-25-click-01";
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
  "/static/dashboard/icons/aquo-192.png",
  "/static/dashboard/icons/aquo-192-maskable.png",
  "/static/dashboard/icons/aquo-512.png",
  "/static/dashboard/icons/aquo-512-maskable.png",
  "/static/dashboard/icons/aquo-apple-touch.png",
  "/static/dashboard/icons/aquo-favicon-32.png",
  "/static/dashboard/icons/aquo-favicon-48.png",
];

function log(...args) {
  console.log("[SW-DASH]", ...args);
}

function warn(...args) {
  console.warn("[SW-DASH]", ...args);
}

function isSameOrigin(url) {
  try {
    return new URL(url).origin === self.location.origin;
  } catch {
    return false;
  }
}

function isHtml(request) {
  return (
    request.mode === "navigate" ||
    (request.headers.get("accept") || "").includes("text/html")
  );
}

function isImage(request) {
  return (
    request.destination === "image" ||
    request.url.includes("/media/") ||
    /\.(png|jpg|jpeg|gif|webp|svg)$/i.test(request.url)
  );
}

function isStaticAsset(request) {
  return (
    request.url.includes("/static/") ||
    request.destination === "style" ||
    request.destination === "script" ||
    request.destination === "font"
  );
}

function shouldBypassCache(request) {
  const url = new URL(request.url);

  if (url.pathname.startsWith("/admin/")) return true;
  if (url.pathname.startsWith("/logout/")) return true;
  if (url.pathname.startsWith("/login/")) return true;

  // No cachear pantallas HTML críticas
  if (url.pathname === "/dashboard") return true;
  if (url.pathname === "/dashboard/") return true;
  if (url.pathname === "/dashboard/inicio/") return true;
  if (url.pathname === "/dashboard/home/") return true;

  return false;
}

async function safePut(cacheName, request, response) {
  try {
    if (!isSameOrigin(request.url)) return;
    if (!response || response.status !== 200) return;

    const cache = await caches.open(cacheName);
    await cache.put(request, response.clone());
  } catch (e) {
    warn("safePut error:", e);
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
      const staticCache = await caches.open(CACHE.static);
      const off = await staticCache.match("/dashboard/offline/");
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
      warn("precache fail:", u, e);
    }
  }
}

self.addEventListener("install", (event) => {
  log("INSTALL", VERSION);

  event.waitUntil(
    (async () => {
      const cache = await caches.open(CACHE.static);
      await precacheAll(cache, PRECACHE_URLS);
      await self.skipWaiting();
    })()
  );
});

self.addEventListener("activate", (event) => {
  log("ACTIVATE", VERSION);

  event.waitUntil(
    (async () => {
      const keys = await caches.keys();
      const allow = new Set([CACHE.static, CACHE.pages, CACHE.images]);

      await Promise.all(
        keys.map((k) => {
          if (!allow.has(k)) {
            log("Deleting old cache:", k);
            return caches.delete(k);
          }
          return null;
        })
      );

      await self.clients.claim();
    })()
  );
});

self.addEventListener("message", (event) => {
  if (event.data === "SKIP_WAITING") {
    log("message: SKIP_WAITING");
    self.skipWaiting();
  }
});

self.addEventListener("push", (event) => {
  let data = {};

  try {
    data = event.data ? event.data.json() : {};
  } catch (e) {
    data = {
      title: "AQUO 360",
      body: event.data ? event.data.text() : "Nueva notificación",
    };
  }

  const title = data.title || "AQUO 360";
  const body = data.body || data.message || "Tienes una nueva notificación.";
  const url = data.url || "/dashboard/home/";
  const tag =
    data.tag && String(data.tag).trim()
      ? String(data.tag).trim()
      : `aquo360-${Date.now()}`;

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

// Navegación al tocar una notificación, incluso con la PWA cerrada.
self.addEventListener("notificationclick", (event) => {
  const notification = event.notification;
  const rawUrl = notification?.data?.url || "/dashboard/notificaciones/";
  notification.close();

  event.waitUntil((async () => {
    // Nunca permitir destinos externos desde una carga push.
    let target;
    try {
      const parsed = new URL(rawUrl, self.location.origin);
      target = parsed.origin === self.location.origin &&
        parsed.pathname.startsWith("/dashboard/")
        ? parsed.href : new URL("/dashboard/notificaciones/", self.location.origin).href;
    } catch (error) {
      target = new URL("/dashboard/notificaciones/", self.location.origin).href;
    }

    const windows = await clients.matchAll({type: "window", includeUncontrolled: true});
    const existing = windows.find((windowClient) => {
      try {
        const current = new URL(windowClient.url);
        return current.origin === self.location.origin &&
          current.pathname.startsWith("/dashboard/");
      } catch (error) { return false; }
    });

    if (existing) {
      try {
        // Navegar primero y enfocar la ventana devuelta, no la anterior.
        const navigated = await existing.navigate(target);
        if (navigated) {
          await navigated.focus();
          return;
        }
      } catch (error) {
        warn("notificationclick: no se pudo navegar ventana existente", error);
      }
    }

    // Si no hay ventana o falló navigate, abrir una nueva.
    if (clients.openWindow) {
      const opened = await clients.openWindow(target);
      if (opened && "focus" in opened) await opened.focus();
    }
  })());
});

self.addEventListener("fetch", (event) => {
  const req = event.request;

  if (req.method !== "GET") return;
  if (!isSameOrigin(req.url)) return;

  if (shouldBypassCache(req)) {
    if (isHtml(req)) {
      event.respondWith(networkOnlyHtml(req));
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