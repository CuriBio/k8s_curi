import argparse
import glob
import json
import os
import re
import sys
import subprocess

import requests


K8S_REPO_BASE_URL = "https://api.github.com/repos/CuriBio/k8s_curi"


SVC_PATH_PATTERN = "deployments/**/services/*"
WORKER_PATH_PATTERN = "jobs/**/*-worker"
JOBS_OPERATOR_PATH = "jobs/jobs-operator/jobs-operator"
QUEUE_PROCESSOR_PATH = "jobs/queue-processor"
ALL_SVC_PATHS = frozenset(
    [
        *glob.glob(SVC_PATH_PATTERN, recursive=True),
        *glob.glob(WORKER_PATH_PATTERN, recursive=True),
        JOBS_OPERATOR_PATH,
        QUEUE_PROCESSOR_PATH,
    ]
)


def parse_py_dep_version(svc_path: str, dep_name: str) -> str:
    req_file = os.path.join(svc_path, "src", "requirements.txt")

    with open(req_file) as f:
        for line in f.readlines():
            if line.startswith(dep_name):
                return line.strip().split("==")[-1]

    raise Exception(f"{dep_name} not found in {req_file}")


def get_svc_version(svc_path: str) -> str:
    # Version will be hardcoded in each services config file
    config_file = os.path.join(svc_path, "src", "core", "config.py")
    with open(config_file) as f:
        for line in f.readlines():
            if line.startswith("VERSION"):
                return line.strip().split(" = ")[-1].replace('"', "")

    raise Exception(f"Version not found in {config_file}")


def get_dir_args(*dirs: list[str]) -> list[str]:
    return [f"{dir_}/{arg}" for dir_ in dirs for arg in ("src/**", "log_config.yaml", "Dockerfile")]


def get_svc_name_from_path(file_path: str):
    return file_path.split("/src")[0] if "/src" in file_path else os.path.dirname(file_path)


def find_changed_svcs(sha: str):
    patterns_to_check = (SVC_PATH_PATTERN, WORKER_PATH_PATTERN, JOBS_OPERATOR_PATH, QUEUE_PROCESSOR_PATH)

    completed_process = subprocess.run(
        ["git", "--no-pager", "diff", sha, "--name-only", "--", *get_dir_args(*patterns_to_check)],
        stdout=subprocess.PIPE,
    )

    changed_paths_list = completed_process.stdout.decode("utf-8").split("\n")[:-1]
    # include the svcs that actually had files changed
    changed_svc_paths = set(get_svc_name_from_path(ch_path) for ch_path in changed_paths_list)

    list_to_return = []
    for ch_path in changed_svc_paths:
        if "pheno" in ch_path:
            # ignoring all pheno related changes at the moment
            continue

        if "queue-processor" in ch_path:
            dep_name, svc = ch_path.split("/")
            dep_type = None
        else:
            dep_type, dep_name, *_, svc = ch_path.split("/")

        if dep_type == "deployments":
            if svc == "pulse3d":
                svc = "pulse3d_api"
            if svc == "advanced-analysis":
                svc = "advanced-analysis-api"

        # need to output the pulse3d package version so it can be included in the name of the pulse3d-worker docker image
        if svc == "pulse3d-worker":
            version = parse_py_dep_version(ch_path, "pulse3d")
        elif svc == "advanced-analysis-worker":
            # TODO remove "dummy" here once it's removed
            version = parse_py_dep_version(os.path.join(ch_path, "dummy"), "advanced-analysis")
        elif svc in ("queue-processor", "jobs-operator") or dep_type == "deployments":
            # get version from service config to tag docker images
            version = get_svc_version(ch_path)
        else:
            # protecting any missed changes
            version = "latest"

        list_to_return.append({"path": ch_path, "deployment": dep_name, "service": svc, "version": version})

    return list_to_return


def find_changed_tf(sha: str):
    # get diff for all directories containing changed tf excluding those found in /cluster and /core
    completed_process = subprocess.run(
        ["git", "--no-pager", "diff", sha, "--name-only", "--", "*.tf", "*.tfvars", ":!cluster", ":!core"],
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
    comment = re.sub(r"WITH PASSWORD '\S+'", "WITH PASSWORD ****", comment)

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
            print(json.dumps(changed))  # allow-print

            for c in changed:
                context = c["path"] if args.terraform else f"{c['deployment']}/{c['service']}"
                task_failed |= set_status(context, args.status, args.sha, token)

        if args.context:
            task_failed |= set_status(args.context, args.status, args.sha, token)

    elif args.pr_number and args.pr_comment:
        task_failed |= post_pr_comment(args.pr_number, args.pr_comment, token)

    sys.exit(int(task_failed))
