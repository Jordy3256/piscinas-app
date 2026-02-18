/* dashboard/static/dashboard/sw-dashboard.js */

const VERSION = "v1.2.3";

const CACHE = {
  static: `static-${VERSION}`,
  pages: `pages-${VERSION}`,
  images: `images-${VERSION}`,
};

const PRECACHE_URLS = [
  "/dashboard/",
  "/dashboard/home/",
  "/dashboard/offline/",
  "/dashboard/manifest.json",

  "/static/dashboard/icons/icon-192.png",
  "/static/dashboard/icons/icon-192-maskable.png",
  "/static/dashboard/icons/icon-512.png",
  "/static/dashboard/icons/icon-512-maskable.png",
];

function log(...args) { console.log("[SW-DASH]", ...args); }
function warn(...args) { console.warn("[SW-DASH]", ...args); }

function isSameOrigin(url) {
  try { return new URL(url).origin === self.location.origin; } catch { return false; }
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
  return false;
}

function normalizeNavigate(req) {
  const url = new URL(req.url);
  if (url.pathname.startsWith("/dashboard/")) {
    url.search = "";
    url.hash = "";
    return new Request(url.toString(), { method: "GET", credentials: "same-origin", redirect: "follow" });
  }
  return req;
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
  const fresh = await fetch(request);
  await safePut(cacheName, request, fresh);
  return fresh;
}

async function networkFirst(request, cacheName) {
  const cache = await caches.open(cacheName);
  try {
    const fresh = await fetch(request);
    await safePut(cacheName, request, fresh);
    return fresh;
  } catch (e) {
    const cached = await cache.match(request);
    if (cached) return cached;

    if (isHtml(request)) {
      const off = await cache.match("/dashboard/offline/");
      if (off) return off;
      const home = await cache.match("/dashboard/home/");
      if (home) return home;
    }
    throw e;
  }
}

self.addEventListener("install", (event) => {
  log("INSTALL", VERSION, "scope:", self.registration.scope);
  event.waitUntil((async () => {
    const cache = await caches.open(CACHE.static);
    await cache.addAll(PRECACHE_URLS.map((u) => new Request(u, { cache: "reload" })));
    await self.skipWaiting();
  })());
});

self.addEventListener("activate", (event) => {
  log("ACTIVATE", VERSION, "scope:", self.registration.scope);
  event.waitUntil((async () => {
    const keys = await caches.keys();
    const allow = new Set([CACHE.static, CACHE.pages, CACHE.images]);
    await Promise.all(keys.map((k) => (!allow.has(k) ? caches.delete(k) : null)));
    await self.clients.claim();
  })());
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;
  if (!isSameOrigin(req.url)) return;
  if (shouldBypassCache(req)) return;

  const request = isHtml(req) ? normalizeNavigate(req) : req;

  if (isHtml(request)) {
    event.respondWith(networkFirst(request, CACHE.pages));
    return;
  }
  if (isImage(request)) {
    event.respondWith(cacheFirst(request, CACHE.images));
    return;
  }
  if (isStaticAsset(request)) {
    event.respondWith(cacheFirst(request, CACHE.static));
    return;
  }
  event.respondWith(networkFirst(request, CACHE.pages));
});
