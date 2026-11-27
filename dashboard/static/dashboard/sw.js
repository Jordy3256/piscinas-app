/* Compatibilidad con registros antiguos. */
if (new URL(self.registration.scope).pathname !== "/dashboard/") {
  self.addEventListener("install", event => event.waitUntil(self.skipWaiting()));
  self.addEventListener("activate", event => event.waitUntil(self.registration.unregister()));
} else {
  importScripts("/dashboard/sw.js");
}
