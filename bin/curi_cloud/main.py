import argparse
import logging
import os
import pkgutil

from mako.template import Template

log = logging.getLogger(__name__)


def _write_template(tmpl, outf, **kwargs):
    try:
        template = Template(pkgutil.get_data(__name__, f"templates/{tmpl}").decode())
        with open(outf, "w") as f:
            log.info(f"Writing template {tmpl} to {outf}")
            f.write(template.render(**kwargs))
    except Exception as e:
        raise Exception(f"Error writing template {tmpl} to {outf}, {e}")


def add_services(deployment_dir, deployment_name, service_name):
    """Adds new service templates to given deployment"""
    log.info(f"Adding {service_name} to {deployment_dir}/{deployment_name}")
    service_dir = f"{deployment_dir}/{deployment_name}/services/{service_name}"
    # tf_dir = f'{deployment_dir}/terraform/{deployment_name}/{service_name}'

    if os.path.isdir(service_dir):
        log.warning(f"Service {service_name} already exists at {service_dir}, skipping")
        return

    # Create service directories
    os.makedirs(f"{service_dir}/src")
    os.makedirs(f"{service_dir}/manifests")
    os.makedirs(f"{service_dir}/terraform")

    _write_template("service_makefile.mako", f"{service_dir}/Makefile", service_name=service_name)
    _write_template("service_dockerfile.mako", f"{service_dir}/Dockerfile")
    _write_template("tf_input.mako", f"{service_dir}/terraform/input.tf")
    _write_template("tf_output.mako", f"{service_dir}/terraform/output.tf")
    _write_template("tf_main.mako", f"{service_dir}/terraform/main.tf")
    _write_template("service_app.mako", f"{service_dir}/src/main.py")


def add_deployment(deployment_dir, deployment_name):
    """Adds new deployment directory"""
    deployment_path = f"{deployment_dir}/{deployment_name}"
    # tf_path = f"{deployment_dir}/terraform"

    if os.path.isdir(deployment_path):
        log.warning(f"Deployment {deployment_name} already exists at {deployment_path}, skipping")
        return

    # os.makedirs(f'{deployment_dir}/manifests')
    os.makedirs(f"{deployment_path}/manifests")
    os.makedirs(f"{deployment_path}/services")
    os.makedirs(f"{deployment_path}/terraform")

    if not os.path.isfile(f"{deployment_dir}/terraform/main.tf"):
        _write_template("tf_main.mako", f"{deployment_dir}/main.tf")

    if not os.path.isfile(f"{deployment_path}/main.tf"):
        _write_template("tf_main.mako", f"{deployment_path}/terraform/main.tf")
    if not os.path.isfile(f"{deployment_path}/terraform/input.tf"):
        _write_template("tf_main.mako", f"{deployment_path}/terraform/input.tf")
    if not os.path.isfile(f"{deployment_path}/terraform/output.tf"):
        _write_template("tf_main.mako", f"{deployment_path}/terraform/output.tf")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="curi cloud cli")
    parser.add_argument("--directory", default=".", help="Repo directory")
    parser.add_argument("-ns", "--new-service", type=str, help="Add new service(s) template")
    parser.add_argument("-dp", "--deployment", type=str, help="Set deployment")
    args = parser.parse_args()

    work_dir = os.path.expanduser(args.directory)

    try:
        if args.new_service:
            if not args.deployment:
                parser.error("--new-service requires setting --deployment")

            if not os.path.isdir(f"{work_dir}/deployments/{args.deployment}"):
                add_deployment(f"{work_dir}/deployments", args.deployment)

            for service_name in args.new_service.split(","):
                deployment_dir = f"{work_dir}/deployments"
                add_services(deployment_dir, args.deployment, service_name)

    except Exception as e:
        log.error(f"{e}")
        exit()

    # parser.add_argument('--apply', action='store_true')
    # parser.add_argument('--destroy', action='store_true')
    # parser.add_argument('--no-color', action='store_true')
    # parser.add_argument('--output', action='store_true', help='get terraform output')
    # parser.add_argument('--refresh', action='store_true')
    # parser.add_argument(
    #     '--infra_dir', default='./infra/environments/', type=str, help='Terraform infrastructure directory',
    # )

    # if args.workspace in ['prod', 'test', 'modl'] and args.destroy:
    #     logger.error(f'Workspace {args.workspace} can't be destroyed')
    #     sys.exit(1)
