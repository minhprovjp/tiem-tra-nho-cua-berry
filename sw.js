// Bản đóng cửa: xoá toàn bộ game đã lưu trên máy người chơi rồi tự gỡ.
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', e => {
  e.waitUntil((async () => {
    for (const k of await caches.keys()) await caches.delete(k);
    await self.registration.unregister();
    for (const c of await self.clients.matchAll({ type: 'window' })) c.navigate(c.url);
  })());
});
self.addEventListener('fetch', () => {}); // không giữ gì, luôn lấy từ mạng
