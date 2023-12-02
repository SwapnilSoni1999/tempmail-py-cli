def join_addresses(data):
    return ", ".join([f"{d['address']} ({d['name']})" for d in data])


def print_formatted_mail(payload):
    print("Mail ID:", payload["id"])
    print(
        "From:",
        payload["from"]["address"],
        f"({payload['from']['name']})" if len(payload["from"]["name"]) else "",
    )
    print("To:", join_addresses(payload["to"]))

    if "cc" in payload and len(payload["cc"]):
        print("CC:", join_addresses(payload["cc"]))

    if "bcc" in payload and len(payload["bcc"]):
        print("BCC:", join_addresses(payload["bcc"]))

    print("Subject:", payload["subject"])
    print()
    print("Body:", payload["text"])
    print()
