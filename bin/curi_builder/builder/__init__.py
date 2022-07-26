import argparse
import json
import glob
import os
import sys
import subprocess

import requests


K8S_REPO_BASE_URL = "https://api.github.com/repos/CuriBio/k8s_curi"


def get_diff(sha: str, path: str):
    r = subprocess.run(["git", "--no-pager", "diff", sha, "--name-only", path], stdout=subprocess.PIPE)
    return r.stdout.decode("utf-8").split("\n")[:-1]


def find_changed(sha: str):
    s = get_diff(sha, "./deployments")

    return [
        {
            "path": f"./{'/'.join(x.split('/')[:-2])}",
            "deployment": x.split("/")[1],
            "service": x.replace("/services/pulse3d", "/services/pulse3d_api").split("/")[
                3
            ],  # leaving 'services/' to prevent switching other pulse3d
        }
        for x in s
        if "service" in x  # remove terraform changes
    ]
# def find_changed(sha):
#     list_to_return = []

#     for dir in ["./deployments","./jobs"]:
#         completed_process =  subprocess.run(
#             ["git", "--no-pager", "diff", sha, "--name-only", dir], stdout=subprocess.PIPE
#         )
#         changes_list = completed_process.stdout.decode("utf-8").split("\n")[:-1]
#         list_to_return += [
#             {
#                 "path": f"./{'/'.join(ch.split('/')[:-2])}",
#                 "deployment": ch.split("/")[1],
#                 # Splits the path into an array and return the element right before the src folder.
#                 # If its the /deployment pulse3d directory, then change the service name from pulse3d to pulse3d_api
#                 # Else set service name to be the folder one above src
#                 "service": "pulse3d_api" if ch.split("/")[ch.split("/").index("src") - 1] == "pulse3d" and dir == "./deployments" else ch.split("/")[ch.split("/").index("src") - 1]
#             }
#             for ch in changes_list
#         ]

#     return list_to_return
    # ds = glob.glob('./deployments/**/Dockerfile', recursive=True)
    # return [{"path": f"./{'/'.join(d.split('/')[:-1])}", "deployment": d.split("/")[2], "service": d.split("/")[4]} for d in ds]


def find_changed_tf(sha):
    # get diff for all directories containing changing tf
    changed_paths = get_diff(sha, "./deployments") + get_diff(sha, "./frontend") + get_diff(sha, "./jobs")
    # get only the terraform directory path
    tf_only_paths = [
        path.split("/terraform")[0] + "/terraform" for path in changed_paths if "terraform" in path
    ]
    # return unique tf paths
    return [{"path": path.split("/terraform")[0] + "/terraform"} for path in list(set(tf_only_paths))]


def set_status(build, status, sha, token):
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
    parser.add_argument("--terraform", action=argparse.BooleanOptionalAction, default=False)
    args = parser.parse_args()

    token = os.getenv("TOKEN")

    task_failed = False

    if args.changed and args.sha and token:

        changed = find_changed_tf(args.sha) if args.terraform else find_changed(args.sha)
        print(json.dumps(changed))

        if args.status and not args.terraform:
            for c in changed:
                context = c["path"] if args.terraform else f"{c['deployment']}/{c['service']}"
                task_failed |= set_status(context, args.status, args.sha, token)

    elif args.status and args.context and token:
        task_failed |= set_status(args.context, args.status, args.sha, token)
    elif args.pr_number and args.pr_comment:
        task_failed |= post_pr_comment(args.pr_number, args.pr_comment, token)

    sys.exit(int(task_failed))
