import requests
import time
import json
import schedule
from mailtm_utils import print_formatted_mail
import time
from getpass import getpass

MAILTM_HEADERS = {"Accept": "application/json", "Content-Type": "application/json"}

MAILTM_AUTH_HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "Authorization": "",
}

HOST = "https://api.mail.tm"
displayed_mail_ids: list[str] = []


class MailTmError(Exception):
    pass


def _make_mailtm_request(request_fn, timeout=600):
    tstart = time.monotonic()
    error = None
    status_code = None
    while time.monotonic() - tstart < timeout:
        try:
            r = request_fn()
            status_code = r.status_code
            if status_code == 200 or status_code == 201:
                return r.json()
            if status_code != 429:
                break
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            error = e
        time.sleep(1.0)

    if error is not None:
        raise MailTmError(e) from error
    if status_code is not None:
        raise MailTmError(f"Status code: {status_code}")
    if time.monotonic() - tstart >= timeout:
        raise MailTmError("timeout")
    raise MailTmError("unknown error")


def get_mailtm_domains():
    def _domain_req():
        return requests.get("https://api.mail.tm/domains", headers=MAILTM_HEADERS)

    r = _make_mailtm_request(_domain_req)

    return [x["domain"] for x in r]


def get_mailtm_domains_auth():
    def _domain_req_auth():
        return requests.get(f"{HOST}/domains", headers=MAILTM_AUTH_HEADERS)

    r = _make_mailtm_request(_domain_req_auth)

    return [x["domain"] for x in r]


def create_mailtm_account(address, password):
    account = json.dumps({"address": address, "password": password})

    def _acc_req():
        return requests.post(
            "https://api.mail.tm/accounts", data=account, headers=MAILTM_HEADERS
        )

    r = _make_mailtm_request(_acc_req)
    assert len(r["id"]) > 0


def get_account_token(address: str, password: str):
    account = json.dumps({"address": address, "password": password})

    def _get_token():
        return requests.post(f"{HOST}/token", data=account, headers=MAILTM_HEADERS)

    r = _make_mailtm_request(_get_token)
    return r


def get_mails(page=1):
    def _get_messages_req():
        return requests.get(
            f"{HOST}/messages", headers=MAILTM_AUTH_HEADERS, params={"page": page}
        )

    r = _make_mailtm_request(_get_messages_req)
    return r


def get_mail_by_id(mail_id: str):
    def _get_message_by_id():
        return requests.get(f"{HOST}/messages/{mail_id}", headers=MAILTM_AUTH_HEADERS)

    r = _make_mailtm_request(_get_message_by_id)

    # def _mark_read():
    #     return requests.patch(f"{HOST}/messages/{mail_id}", headers=MAILTM_AUTH_HEADERS)

    # _make_mailtm_request(_mark_read)

    return r


def get_new_mails(page=1):
    mails = get_mails(page)
    new_mails = []

    for mail in mails:
        if mail["id"] not in displayed_mail_ids:
            new_mails.append(mail)

    if len(mails) > 0:
        if len(new_mails) == len(mails):
            n_mails = get_new_mails(page + 1)
            new_mails.extend(n_mails)

    return new_mails


def monitor():
    new_mails = get_new_mails()

    new_mails_count = len(new_mails)
    if new_mails_count > 0:
        print(f"\tYou've got {new_mails_count} new mail(s).\n")

        for mail in new_mails:
            opened_mail = get_mail_by_id(mail["id"])
            print_formatted_mail(opened_mail)
            displayed_mail_ids.append(mail["id"])


if __name__ == "__main__":
    domains = get_mailtm_domains()
    print("Available Domains:", domains)

    domain_choice = (
        int(
            input(
                f"Please enter the number whichever domain you want to choose (eg. 1 for {domains[0]}): "
            )
        )
        - 1
    )

    if domain_choice > len(domains):
        print("Error: Please choose a valid number and try again.")
        raise Exception("Invalid domain selection")

    username = input(
        f"Enter username for {domains[domain_choice]} (eg. input 'user' will be user@{domains[domain_choice]}) [NOTE: Username should be minimum of 10 characters]: "
    )

    if len(username) <= 10:
        print(
            "Error: Username must be greater than or eq to 10 characters, Please retry and enter valid username."
        )
        raise Exception("Invalid username")

    user_email = f"{username}@{domains[domain_choice]}"
    user_password = getpass(f"Enter password for {user_email}: ")

    create_mailtm_account(user_email, user_password)
    print("Account created!")

    token_data = get_account_token(user_email, user_password)
    print("Account Token:", token_data["token"])
    print("Account ID:", token_data["id"])
    print()

    token = token_data["token"]
    MAILTM_AUTH_HEADERS["Authorization"] = f"Bearer {token}"

    # print(get_mailtm_domains_auth())
    mails = get_mails()
    # print(mails)
    if len(mails):
        displayed_mail_ids = [d["id"] for d in mails]

    print(
        f"Monitoring inbox for {user_email}... All the newly incoming mails will be printed here."
    )
    schedule.every(1).second.do(monitor)

    while True:
        schedule.run_pending()
        time.sleep(1)

    # print(specific_mail)
