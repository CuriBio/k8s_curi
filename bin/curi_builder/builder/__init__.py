import argparse
import json
import glob
import os
import sys
import subprocess

import requests


K8S_REPO_BASE_URL = "https://api.github.com/repos/CuriBio/k8s_curi"


def find_changed(sha):
    r = subprocess.run(
        ["git", "--no-pager", "diff", sha, "--name-only", "./deployments"], stdout=subprocess.PIPE
    )
    s = r.stdout.decode("utf-8").split("\n")[:-1]

    return [
        {
            "path": f"./{'/'.join(x.split('/')[:-2])}",
            "deployment": x.split("/")[1],
            "service": x.replace("/services/pulse3d", "/services/pulse3d_api").split("/")[
                3
            ],  # leaving services to prevent switching for pulse3d-worker
        }
        for x in s
    ]

    # ds = glob.glob('./deployments/**/Dockerfile', recursive=True)
    # return [{"path": f"./{'/'.join(d.split('/')[:-1])}", "deployment": d.split("/")[2], "service": d.split("/")[4]} for d in ds]


def set_build_status(build, status, sha, token):
    req = {
        "headers": {
            "Authorization": f"Bearer {token.strip()}",
            "Content-Type": "application/json",
        },
        "data": json.dumps({"state": status, "context": build}),
        "url": f"{K8S_REPO_BASE_URL}/statuses/{sha}",
    }

    response = requests.post(**req)
    return response.status_code != 201


def post_pr_comment(pr_number, comment, token):
    req = {
        "headers": {"Authorization": f"Bearer {token.strip()}"},
        "json": {"body": comment},
        "url": f"{K8S_REPO_BASE_URL}/issues/{pr_number}/comments",
    }

    response = requests.post(**req)
    return response.status_code != 201


def main():
    parser = argparse.ArgumentParser(description="Process some integers.")
    parser.add_argument("--changed", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--status", type=str, default=None)
    parser.add_argument("--context", type=str, default=None)
    parser.add_argument("--sha", type=str)
    parser.add_argument("--pr-number", type=int, default=None)
    parser.add_argument("--pr-comment", type=str, default=None)
    args = parser.parse_args()

    token = os.getenv("TOKEN")

    task_failed = False

    if args.changed and args.sha and token:
        changed = find_changed(args.sha)
        print(json.dumps(changed))

        if args.status:
            for c in changed:
                task_failed |= set_build_status(
                    f"{c['deployment']}/{c['service']}", args.status, args.sha, token
                )
    elif args.status and args.context and token:
        task_failed |= set_build_status(args.context, args.status, args.sha, token)
    elif args.pr_number and args.pr_comment:
        task_failed |= post_pr_comment(args.pr_number, args.pr_comment, token)

    sys.exit(int(task_failed))
