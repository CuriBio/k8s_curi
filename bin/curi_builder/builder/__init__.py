import argparse
import json
import os
import sys
import subprocess

import requests


K8S_REPO_BASE_URL = "https://api.github.com/repos/CuriBio/k8s_curi"


def parse_py_dep_version(file_path: str, dep_name: str) -> str:
    with open(file_path) as f:
        for line in f.readlines():
            if line.startswith(dep_name):
                return line.split("==")[-1]

    raise Exception(f"{dep_name} not found in {file_path}")


def find_changed(sha: str):
    list_to_return = []

    for dir in ["./deployments", "./jobs"]:
        completed_process = subprocess.run(
            ["git", "--no-pager", "diff", sha, "--name-only", "--", dir, ":!*.tf"], stdout=subprocess.PIPE
        )
        changed_paths_list = completed_process.stdout.decode("utf-8").split("\n")[:-1]

        for ch_path in changed_paths_list:
            subdirs = ch_path.split("/")

            # set service name to be the folder one above src
            svc = subdirs[subdirs.index("src") - 1]
            if svc == "pulse3d" and dir == "./deployments":
                # if it's the /deployment pulse3d directory, then change the service name from pulse3d to pulse3d_api
                svc = "pulse3d_api"

            # need to output the pulse3d package version so it can be included in the name of the pulse3d-worker docker image
            version = (
                parse_py_dep_version(ch_path, "pulse3d")
                if dir == "./jobs" and os.path.basename(ch_path) == "requirements.txt"
                else "latest"
            )

            # TODO test all this in a PR

            list_to_return.append(
                {
                    "path": f"./{'/'.join(subdirs[:-2])}",
                    "deployment": subdirs[1],
                    "svc": svc,
                    "version": version,
                }
            )

    return list_to_return


def find_changed_tf(sha):
    # get diff for all directories containing changed tf excluding those found in /cluster and /core
    completed_process = subprocess.run(
        ["git", "--no-pager", "diff", sha, "--name-only", "--", "*.tf", ":!cluster", ":!core"],
        stdout=subprocess.PIPE,
    )
    changed_paths = completed_process.stdout.decode("utf-8").split("\n")[:-1]
    # get only the first terraform directory, remove files
    tf_dirs = set("".join(path.partition("/terraform")[:2]) for path in changed_paths)

    return [{"path": path} for path in tf_dirs]


def set_status(context, status, sha, token):
    req = {
        "headers": {"Authorization": f"Bearer {token.strip()}", "Content-Type": "application/json"},
        "data": json.dumps({"state": status, "context": context}),
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
    if not token:
        raise Exception("No token set")

    task_failed = False

    if args.status and args.sha:
        if args.changed:
            changed = (find_changed_tf if args.terraform else find_changed)(args.sha)

            # printing here in order to expose the names of the svcs or terraform files with changes
            # to the process calling this python script. It is not a debug statement, don't delete it
            print(json.dumps(changed))

            for c in changed:
                context = c["path"] if args.terraform else f"{c['deployment']}/{c['service']}"
                task_failed |= set_status(context, args.status, args.sha, token)

        if args.context:
            task_failed |= set_status(args.context, args.status, args.sha, token)

    elif args.pr_number and args.pr_comment:
        task_failed |= post_pr_comment(args.pr_number, args.pr_comment, token)

    sys.exit(int(task_failed))
