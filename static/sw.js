self.addEventListener("install", function (event) {
    self.skipWaiting();
});

self.addEventListener("activate", function (event) {
    event.waitUntil(self.clients.claim());
});


self.addEventListener("push", function (event) {

    let data = {};

    try {
        data = event.data ? event.data.json() : {};
    } catch (e) {
        data = {
            title: "Almoxarifado",
            body: event.data ? event.data.text() : "Nova requisição recebida."
        };
    }

    const title = data.title || "📦 Nova requisição";

    const options = {
        body: data.body || "Uma nova requisição foi recebida.",
        icon: "/static/logo.png.png",
        badge: "/static/logo.png.png",
        tag: data.tag || "almox-nova-requisicao",
        renotify: true,
        requireInteraction: false,
        data: {
            url: data.url || "/painel"
        }
    };

    event.waitUntil(
        self.registration.showNotification(title, options)
    );
});


self.addEventListener("notificationclick", function (event) {

    event.notification.close();

    const url = event.notification.data &&
                event.notification.data.url
                ? event.notification.data.url
                : "/painel";

    event.waitUntil(

        clients.matchAll({
            type: "window",
            includeUncontrolled: true
        }).then(function (clientList) {

            for (const client of clientList) {

                if ("focus" in client) {

                    client.navigate(url);

                    return client.focus();
                }
            }

            if (clients.openWindow) {
                return clients.openWindow(url);
            }
        })

    );
});
