/* dashboard/static/dashboard/sw.js */

const VERSION = "v1.2.3"; // 👈 sube versión para forzar update

// ==========================================================
// ✅ “Modo dual” (ANTI-SW FANTASMA):
// - Si este archivo se registra por error desde /static/...,
//   su scope será /static/... y SE AUTO-DESREGISTRA.
// - Si se registra correctamente desde /dashboard/sw.js,
//   su scope será /dashboard/ y funciona normal.
// ==========================================================
const SCOPE_PATH = (() => {
  try {
    return new URL(self.registration.scope).pathname; // "/dashboard/" o "/static/dashboard/"
  } catch {
    return "";
  }
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

// ✅ Precaching dentro del scope real (/dashboard/)
const PRECACHE_URLS = [
  "/dashboard/",
  "/dashboard/home/",
  "/dashboard/offline/",
  "/dashboard/manifest.json",

  // ✅ Icons
  "/static/dashboard/icons/icon-192.png",
  "/static/dashboard/icons/icon-192-maskable.png",
  "/static/dashboard/icons/icon-512.png",
  "/static/dashboard/icons/icon-512-maskable.png",
];

// ==============================
// Helpers
// ==============================
function log(...args) {
  console.log("[SW]", ...args);
}
function warn(...args) {
  console.warn("[SW]", ...args);
}

function isSameOrigin(url) {
  try {
    return new URL(url).origin === self.location.origin;
  } catch {
    return false;
  }
}

function normalizeRequest(request) {
  const url = new URL(request.url);

  // Solo normalizamos dentro de /dashboard/ (navegación)
  if (url.pathname.startsWith("/dashboard/")) {
    url.search = "";
    url.hash = "";
    return new Request(url.toString(), {
      method: "GET",
      headers: request.headers,
      credentials: "same-origin",
      redirect: "follow",
    });
  }

  return request;
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

  // ✅ No cachear rutas sensibles o que cambian por sesión
  if (url.pathname.startsWith("/admin/")) return true;
  if (url.pathname.startsWith("/logout/")) return true;
  if (url.pathname.startsWith("/login/")) return true;

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

// ==============================
// Strategies
// ==============================
async function cacheFirst(request, cacheName) {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(request);
  if (cached) {
    log("CACHE HIT", cacheName, request.url);
    return cached;
  }

  log("CACHE MISS", cacheName, request.url);
  const fresh = await fetch(request);
  await safePut(cacheName, request, fresh);
  return fresh;
}

async function networkFirst(request, cacheName) {
  const cache = await caches.open(cacheName);

  try {
    log("NETWORK FIRST", cacheName, request.url);
    const fresh = await fetch(request);
    await safePut(cacheName, request, fresh);
    return fresh;
  } catch (e) {
    warn("NETWORK FAIL -> CACHE", cacheName, request.url);

    const cached = await cache.match(request);
    if (cached) {
      log("CACHE FALLBACK HIT", cacheName, request.url);
      return cached;
    }

    // ✅ Fallback SOLO si es navegación
    if (isHtml(request)) {
      const off = await cache.match("/dashboard/offline/");
      if (off) {
        warn("NAV FALLBACK -> /dashboard/offline/");
        return off;
      }

      const home = await cache.match("/dashboard/home/");
      if (home) {
        warn("NAV FALLBACK -> /dashboard/home/");
        return home;
      }
    }

    throw e;
  }
}

// ==============================
// “SW veneno” para scopes incorrectos
// ✅ IMPORTANTE: NO navegar clientes aquí (evita:
// "This service worker is not the client's active service worker.")
// ==============================
async function poisonUnregister() {
  try {
    warn("⚠️ Scope incorrecto:", SCOPE_PATH, "-> unregister()");
    await self.registration.unregister();
    // No hacemos navigate() aquí. El frontend ya limpia y registra el correcto.
  } catch (e) {
    warn("poison unregister error:", e);
  }
}

// ==============================
// INSTALL
// ==============================
self.addEventListener("install", (event) => {
  log("INSTALL", VERSION, "scope:", SCOPE_PATH);

  // ❌ Si se registró desde /static/... no debe funcionar
  if (!IS_DASHBOARD_SCOPE) {
    event.waitUntil(self.skipWaiting());
    return;
  }

  event.waitUntil(
    (async () => {
      try {
        const cache = await caches.open(CACHE.static);
        const reqs = PRECACHE_URLS.map((u) => new Request(u, { cache: "reload" }));
        await cache.addAll(reqs);

        await self.skipWaiting();
        log("PRECACHE OK", CACHE.static, "| skipWaiting OK");
      } catch (e) {
        warn("PRECACHE ERROR:", e);
      }
    })()
  );
});

// ==============================
// ACTIVATE
// ==============================
self.addEventListener("activate", (event) => {
  log("ACTIVATE", VERSION, "scope:", SCOPE_PATH);

  // ❌ Si se registró desde /static/... se elimina solo
  if (!IS_DASHBOARD_SCOPE) {
    event.waitUntil(poisonUnregister());
    return;
  }

  event.waitUntil(
    (async () => {
      try {
        const keys = await caches.keys();
        const allow = new Set([CACHE.static, CACHE.pages, CACHE.images]);

        await Promise.all(
          keys.map((k) => {
            if (!allow.has(k)) {
              log("Deleting old cache:", k);
              return caches.delete(k);
            }
          })
        );

        await self.clients.claim();
        log("clients.claim OK");
      } catch (e) {
        warn("ACTIVATE ERROR:", e);
      }
    })()
  );
});

// ✅ Permite “forzar update” desde el frontend
self.addEventListener("message", (event) => {
  if (event.data === "SKIP_WAITING") {
    log("message: SKIP_WAITING");
    self.skipWaiting();
  }
});

// ==============================
// FETCH
// ==============================
self.addEventListener("fetch", (event) => {
  // ❌ Si no es el scope correcto, no interceptamos nada
  if (!IS_DASHBOARD_SCOPE) return;

  const req = event.request;

  if (req.method !== "GET") return;
  if (!isSameOrigin(req.url)) return; // no cachear CDNs
  if (shouldBypassCache(req)) return;

  const request = isHtml(req) ? normalizeRequest(req) : req;

  // HTML (dashboard) -> network-first con fallback offline/home
  if (isHtml(request)) {
    event.respondWith(networkFirst(request, CACHE.pages));
    return;
  }

  // Imágenes -> cache-first
  if (isImage(request)) {
    event.respondWith(cacheFirst(request, CACHE.images));
    return;
  }

  // Estáticos -> cache-first
  if (isStaticAsset(request)) {
    event.respondWith(cacheFirst(request, CACHE.static));
    return;
  }

  // Otros -> network-first
  event.respondWith(networkFirst(request, CACHE.pages));
});
