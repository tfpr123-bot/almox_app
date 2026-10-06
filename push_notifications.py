import json
import os

from pywebpush import webpush, WebPushException


VAPID_PRIVATE_KEY = os.getenv("VAPID_PRIVATE_KEY", "")
VAPID_CLAIMS_EMAIL = os.getenv(
    "VAPID_CLAIMS_EMAIL",
    "mailto:almox@empresa.com"
)


def enviar_push(subscription_info, titulo, mensagem, url="/painel"):

    if not VAPID_PRIVATE_KEY:
        print("VAPID_PRIVATE_KEY não configurada.")
        return False

    payload = json.dumps({
        "title": titulo,
        "body": mensagem,
        "url": url,
        "tag": "almox-nova-requisicao"
    })

    try:

        webpush(
            subscription_info=subscription_info,
            data=payload,
            vapid_private_key=VAPID_PRIVATE_KEY,
            vapid_claims={
                "sub": VAPID_CLAIMS_EMAIL
            }
        )

        return True

    except WebPushException as exc:

        print("Erro ao enviar push:", exc)

        return False

    except Exception as exc:

        print("Erro inesperado no push:", exc)

        return False
