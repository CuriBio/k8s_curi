import argparse
import json
import glob
import os
import sys
import subprocess

import requests


def find_changed():
    r = subprocess.run(["git", "--no-pager", "diff", "main", "--name-only", "./deployments"], stdout=subprocess.PIPE)
    s = r.stdout.decode("utf-8").split("\n")[:-1]
    return [{"path": f"./{'/'.join(x.split('/')[:-2])}", "deployment": x.split("/")[1], "service": x.split("/")[3]} for x in s]

    # ds = glob.glob('./deployments/**/Dockerfile', recursive=True)
    # return [{"path": f"./{'/'.join(d.split('/')[:-1])}", "deployment": d.split("/")[2], "service": d.split("/")[4]} for d in ds]


def set_build_status(build, status, sha, token):
    req = {
        "headers": {
            "Authorization": f"Bearer {token.strip()}",
            "Content-Type": "application/json",
        },
        "data": json.dumps({"state": status, "context": build}),
        "url": f"https://api.github.com/repos/curibio/k8s_curi/statuses/{sha}",
    }

    response = requests.post(**req)
    if response.status_code == 201:
        sys.exit(0)
    else:
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Process some integers.")
    parser.add_argument("--changed", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--status", type=str, default=None)
    parser.add_argument("--context", type=str, default=None)
    parser.add_argument("--sha", type=str)
    args = parser.parse_args()

    token = os.getenv("TOKEN")

    if args.changed and args.sha and token:
        changed = find_changed()
        print(json.dumps(changed))

        if args.status:
            for c in changed:
                set_build_status(f"{c['deployment']}/{c['service']}", args.status, args.sha, token)
    elif args.status and args.context and token:
        set_build_status(args.context, args.status, args.sha, token)

    sys.exit(0)
