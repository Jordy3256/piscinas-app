/* dashboard/static/dashboard/sw-dashboard.js */

const VERSION = "v1.3.1"; // 👈 sube versión para forzar update

// ==========================================================
// ✅ “Modo dual” (ANTI-SW FANTASMA):
// - Si se registra por error desde /static/... se auto-desregistra.
// - Si se registra bien desde /dashboard/sw.js funciona normal.
// ==========================================================
const SCOPE_PATH = (() => {
  try { return new URL(self.registration.scope).pathname; }
  catch { return ""; }
})();

const EXPECTED_SCOPE = "/dashboard/";
const IS_DASHBOARD_SCOPE = SCOPE_PATH === EXPECTED_SCOPE;

// ==============================
// Caches
// ==============================
const CACHE = {
  static: `static-${VERSION}`,
  pages: `pages-${VERSION}`,
  images: `images-${VERSION}`,
};

// ✅ OJO: precache SOLO de cosas “seguras” (que no dependan de sesión)
// Si /dashboard/ o /dashboard/home/ redirigen a login o fallan, no queremos romper el install.
const PRECACHE_URLS = [
  "/dashboard/manifest.json",
  "/dashboard/offline/",

  "/static/dashboard/icons/icon-192.png",
  "/static/dashboard/icons/icon-192-maskable.png",
  "/static/dashboard/icons/icon-512.png",
  "/static/dashboard/icons/icon-512-maskable.png",
];

// ==============================
// Helpers
// ==============================
function log(...args) { console.log("[SW-DASH]", ...args); }
function warn(...args) { console.warn("[SW-DASH]", ...args); }

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
  return false;
}

function normalizeNavigate(req) {
  const url = new URL(req.url);
  if (url.pathname.startsWith("/dashboard/")) {
    url.search = "";
    url.hash = "";
    return new Request(url.toString(), {
      method: "GET",
      credentials: "same-origin",
      redirect: "follow",
    });
  }
  return req;
}

async function safePut(cacheName, request, response) {
  try {
    if (!isSameOrigin(request.url)) return;
    if (!response) return;

    // Solo guardamos respuestas OK (200)
    if (response.status !== 200) return;

    const cache = await caches.open(cacheName);
    await cache.put(request, response.clone());
  } catch (e) {
    warn("safePut error:", e);
  }
}

// ✅ Precache robusto: NO falla el install si 1 URL falla
async function precacheSafely() {
  const cache = await caches.open(CACHE.static);

  for (const u of PRECACHE_URLS) {
    try {
      const req = new Request(u, { cache: "reload", credentials: "same-origin" });
      const res = await fetch(req);

      if (!res || res.status !== 200) {
        warn("PRECACHE SKIP (not 200):", u, "status:", res?.status);
        continue;
      }

      await cache.put(req, res.clone());
      log("PRECACHE OK:", u);
    } catch (e) {
      warn("PRECACHE FAIL (skip):", u, e);
    }
  }
}

// ==============================
// “SW veneno” para scopes incorrectos
// ==============================
async function poisonUnregister() {
  try {
    warn("⚠️ Scope incorrecto:", SCOPE_PATH, "-> unregister()");
    await self.registration.unregister();
  } catch (e) {
    warn("poison unregister error:", e);
  }
}

// ==============================
// INSTALL
// ==============================
self.addEventListener("install", (event) => {
  log("INSTALL", VERSION, "scope:", SCOPE_PATH);

  if (!IS_DASHBOARD_SCOPE) {
    event.waitUntil(self.skipWaiting());
    return;
  }

  event.waitUntil((async () => {
    await precacheSafely();
    await self.skipWaiting();
    log("INSTALL DONE + skipWaiting()");
  })());
});

// ==============================
// ACTIVATE
// ==============================
self.addEventListener("activate", (event) => {
  log("ACTIVATE", VERSION, "scope:", SCOPE_PATH);

  if (!IS_DASHBOARD_SCOPE) {
    event.waitUntil(poisonUnregister());
    return;
  }

  event.waitUntil((async () => {
    const keys = await caches.keys();
    const allow = new Set([CACHE.static, CACHE.pages, CACHE.images]);

    await Promise.all(keys.map((k) => {
      if (!allow.has(k)) {
        log("Deleting old cache:", k);
        return caches.delete(k);
      }
    }));

    await self.clients.claim();
    log("clients.claim OK");
  })());
});

// ✅ Permite “forzar update”
self.addEventListener("message", (event) => {
  if (event.data === "SKIP_WAITING") {
    log("message: SKIP_WAITING");
    self.skipWaiting();
  }
});

// ==============================
// Strategies
// ==============================
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

    // Fallback navegación
    if (isHtml(request)) {
      const off = await cache.match("/dashboard/offline/");
      if (off) return off;
    }
    throw e;
  }
}

// ==============================
// FETCH
// ==============================
self.addEventListener("fetch", (event) => {
  if (!IS_DASHBOARD_SCOPE) return;

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