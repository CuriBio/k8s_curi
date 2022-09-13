import argparse
import glob
import json
import os
import sys
import subprocess

import requests

from typing import List


K8S_REPO_BASE_URL = "https://api.github.com/repos/CuriBio/k8s_curi"


SVC_PATH_PATTERN = "deployments/**/services/*"
WORKER_PATH_PATTERN = "jobs/**/*-worker"
ALL_SVC_PATHS = frozenset(
    [*glob.glob(SVC_PATH_PATTERN, recursive=True), *glob.glob(WORKER_PATH_PATTERN, recursive=True)]
)

CORE_LIB_PATH = "core/lib"


def parse_py_dep_version(svc_path: str, dep_name: str) -> str:
    req_file = os.path.join(svc_path, "src", "requirements.txt")
    with open(req_file) as f:
        for line in f.readlines():
            if line.startswith(dep_name):
                return line.strip().split("==")[-1]

    raise Exception(f"{dep_name} not found in {req_file}")


def get_dir_args(*dirs: List[str]) -> List[str]:
    return [arg for dir_ in dirs for arg in ("--", dir_)]


def find_changed_svcs(sha: str):
    patterns_to_check = [f"{path}/**" for path in (SVC_PATH_PATTERN, WORKER_PATH_PATTERN, CORE_LIB_PATH)]

    completed_process = subprocess.run(
        ["git", "--no-pager", "diff", sha, "--name-only", *get_dir_args(*patterns_to_check), ":!*.tf"],
        stdout=subprocess.PIPE,
    )

    changed_paths_list = completed_process.stdout.decode("utf-8").split("\n")[:-1]

    # if any core lib files were changed, consider all svcs changed,
    # otherwise just include the svcs that actually had files changed
    if any(ch_path.startswith(CORE_LIB_PATH) for ch_path in changed_paths_list):
        # Tanner (9/8/22): building the pheno svcs is causing issues in CI, so filtering them out here
        changed_svc_paths = set(path for path in ALL_SVC_PATHS if "pheno" not in path)
    else:
        changed_svc_paths = set(ch_path.split("/src")[0] for ch_path in changed_paths_list)

    list_to_return = []
    for ch_path in changed_svc_paths:
        dep_type, dep_name, *_, svc = ch_path.split("/")

        if svc == "pulse3d" and dep_type == "deployments":
            # if it's the pulse3d svc under ./deployments/, then change the svc name from pulse3d to pulse3d_api
            svc = "pulse3d_api"

        # need to output the pulse3d package version so it can be included in the name of the pulse3d-worker docker image
        version = parse_py_dep_version(ch_path, "pulse3d") if svc == "pulse3d-worker" else "latest"

        list_to_return.append({"path": ch_path, "deployment": dep_name, "service": svc, "version": version})

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
    parser.add_argument("--base-sha", type=str, default=None)
    parser.add_argument("--pr-number", type=int, default=None)
    parser.add_argument("--pr-comment", type=str, default=None)
    parser.add_argument("--terraform", action=argparse.BooleanOptionalAction, default=False)
    args = parser.parse_args()

    token = os.getenv("TOKEN")
    if not token:
        raise Exception("No token set")

    task_failed = False

    if args.status and args.sha:
        if args.changed and args.base_sha:
            changed = (find_changed_tf if args.terraform else find_changed_svcs)(args.base_sha)

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
