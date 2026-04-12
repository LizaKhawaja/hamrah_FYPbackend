from firebase_admin import messaging


def send_notification(tokens, title, body):

    if not tokens:
        return

    # if single token list empty safety
    if isinstance(tokens, str):
        tokens = [tokens]

    message = messaging.MulticastMessage(
        notification=messaging.Notification(
            title=title,
            body=body
        ),
        tokens=tokens
    )

    response = messaging.send_each_for_multicast(message)
    print("SUCCESS:", response.success_count)
    print("FAIL:", response.failure_count)

    return response