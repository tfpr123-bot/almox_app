let deferredInstallPrompt = null;

if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("/sw.js")
        .then(() => {
            console.log("Service Worker registrado.");
        })
        .catch((erro) => {
            console.error("Erro ao registrar Service Worker:", erro);
        });
}

window.addEventListener("beforeinstallprompt", function (event) {
    event.preventDefault();
    deferredInstallPrompt = event;
});

async function instalarAlmox() {

    if (!deferredInstallPrompt) {
        alert(
            "O navegador não disponibilizou a instalação agora.\n\n" +
            "No Chrome/Edge, você também pode instalar pelo ícone de instalação " +
            "na barra de endereço."
        );
        return;
    }

    deferredInstallPrompt.prompt();

    await deferredInstallPrompt.userChoice;

    deferredInstallPrompt = null;
}

async function ativarNotificacoes() {

    if (
        !("Notification" in window) ||
        !("serviceWorker" in navigator) ||
        !("PushManager" in window)
    ) {
        alert("Este navegador não suporta notificações push.");
        return;
    }

    try {

        const permissao = await Notification.requestPermission();

        if (permissao !== "granted") {
            alert("Permissão para notificações não concedida.");
            return;
        }

        const registro = await navigator.serviceWorker.ready;

        const resposta = await fetch("/api/push/public-key");

        const dados = await resposta.json();

        if (!dados.ok || !dados.public_key) {
            alert(
                "A chave de notificações ainda não foi configurada no servidor."
            );
            return;
        }

        let subscription =
            await registro.pushManager.getSubscription();

        if (!subscription) {

            subscription =
                await registro.pushManager.subscribe({
                    userVisibleOnly: true,
                    applicationServerKey:
                        urlBase64ToUint8Array(dados.public_key)
                });
        }

        const salvar = await fetch("/api/push/subscribe", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                subscription: subscription
            })
        });

        const resultado = await salvar.json();

        if (resultado.ok) {

            alert(
                "🔔 Notificações ativadas com sucesso!"
            );

        } else {

            alert(
                resultado.erro ||
                "Não foi possível ativar as notificações."
            );
        }

    } catch (erro) {

        console.error(
            "Erro ao ativar notificações:",
            erro
        );

        alert(
            "Não foi possível ativar as notificações.\n\n" +
            erro
        );
    }
}

function urlBase64ToUint8Array(base64String) {

    const padding =
        "=".repeat(
            (4 - base64String.length % 4) % 4
        );

    const base64 =
        (base64String + padding)
            .replace(/-/g, "+")
            .replace(/_/g, "/");

    const rawData = atob(base64);

    return Uint8Array.from(
        [...rawData].map(function (char) {
            return char.charCodeAt(0);
        })
    );
}
