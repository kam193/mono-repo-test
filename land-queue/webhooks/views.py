import json
import requests
from flask import Flask, request, Blueprint
from github import Github
from datetime import datetime, timedelta, timezone
from jwt import JWT, jwk_from_pem
from jwt.utils import get_int_from_datetime

from config import APP_ID, KEY_FILE, WEBHOOKS_LOG_FILE
from utils import log


webhook_views = Blueprint('webhook_views', __name__)

def jwt_token():
    message = {
        "iss": APP_ID,
        "iat": get_int_from_datetime(datetime.now(timezone.utc)),
        "exp": get_int_from_datetime(
            datetime.now(timezone.utc) + timedelta(minutes=10)
        ),
    }
    with open(KEY_FILE, "rb") as fh:
        signing_key = jwk_from_pem(fh.read())

    return JWT().encode(message, signing_key, alg="RS256")


def fetch_cred(installation_id, jwt):
    headers = {
        "Authorization": "Bearer " + jwt,
        "Accept": "application/vnd.github.machine-man-preview+json",
    }
    url = "https://api.github.com/app/installations/%s/access_tokens" % installation_id
    response = requests.post(url, headers=headers)
    return json.loads(response.content)


def get_gh_app(installation_id):
    jwt = jwt_token()
    cred = fetch_cred(installation_id, jwt)
    return Github(cred["token"])


def set_state(state, repo, pr_no, installation_id):
    gh = get_gh_app(installation_id)
    repo = gh.get_repo(repo)
    pull = repo.get_pull(pr_no)
    pull.set_labels(state)


@webhook_views.route("/webhooks", methods=["POST"])
def webhooks():
    log(WEBHOOKS_LOG_FILE, request.data)

    data = json.loads(request.data)
    repo = data["repository"]["full_name"]
    print("Webhooks PR action: ", data["action"], "; repo:", repo)

    if "pull_request" in data:
        sha = data["pull_request"]["head"]["sha"]
        pr_no = data["pull_request"]["number"]
        installation_id = data["installation"]["id"]

        set_state("Build added to queue", repo, pr_no, installation_id)

    return "OK"


@webhook_views.route("/", methods=["GET", "POST"])
def home():
    return "OK"
