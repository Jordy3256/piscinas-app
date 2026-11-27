/* JVAQUA: cache exclusivamente de recursos públicos. */
const VERSION = "jvaqua-static-20261127-08";
const OFFLINE = "/dashboard/offline/";
const ICONS = ["icon-192.png", "icon-512.png", "aquo-192.png", "aquo-512.png"];
function warn(...args) { console.warn("[SW-DASH]", ...args); }
function publicStatic(req) {
  const url = new URL(req.url);
  return url.origin === self.location.origin && url.pathname.startsWith("/static/");
}
async function savePublic(cache, req, res) {
  const control = res.headers.get("Cache-Control") || "";
  if (res.status === 200 && !res.redirected && !/private|no-store|no-cache/i.test(control)) {
    await cache.put(req, res.clone());
  }
}
async function precache() {
  const cache = await caches.open(VERSION);
  // Offline es una página genérica, solicitada sin cookies. El manifest depende del rol.
  const urls = [OFFLINE, ...ICONS.map(n => "/static/dashboard/icons/" + n)];
  await Promise.allSettled(urls.map(async url => {
    const req = new Request(new URL(url, self.location.origin), {credentials: "omit", cache: "reload"});
    const res = await fetch(req);
    await savePublic(cache, req, res);
  }));
}
self.addEventListener("install", event => {
  event.waitUntil((async () => { await precache(); await self.skipWaiting(); })());
});
self.addEventListener("activate", event => {
  event.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.filter(k => k !== VERSION && /^(?:static-v|pages-v|images-v|jvaqua-static-)/.test(k)).map(k => caches.delete(k)));
    await self.clients.claim();
  })());
});
self.addEventListener("message", event => {
  if (event.data === "SKIP_WAITING") event.waitUntil(self.skipWaiting());
});
async function staticAsset(req) {
  // Solo nombres con huella de contenido: los demás usan la caché HTTP normal.
  const cache = await caches.open(VERSION);
  const cached = await cache.match(req);
  if (cached) return cached;
  const res = await fetch(req);
  try { await savePublic(cache, req, res); } catch (e) { warn(e); }
  return res;
}
async function navigate(req) {
  try { return await fetch(req, {cache: "no-store"}); }
  catch (e) {
    const cache = await caches.open(VERSION);
    return (await cache.match(OFFLINE)) || new Response("Sin conexión. Intenta nuevamente.", {status: 503, headers: {"Content-Type": "text/plain; charset=utf-8"}});
  }
}
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

self.addEventListener("fetch", event => {
  const req = event.request;
  if (req.method !== "GET" || new URL(req.url).origin !== self.location.origin) return;
  if (req.mode === "navigate") { event.respondWith(navigate(req)); return; }
  if (publicStatic(req) && /\.[0-9a-f]{12}\.[^/]+$/i.test(new URL(req.url).pathname)) {
    event.respondWith(staticAsset(req));
  }
  // API, manifest, fotos privadas y demás recursos: comportamiento HTTP normal.
});
