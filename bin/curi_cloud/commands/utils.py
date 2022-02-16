import logging
import os
import pkgutil
import yaml

from mako.template import Template

log = logging.getLogger(__name__)

def write_template(tmpl, outf, **kwargs):
    try:
        template = Template(pkgutil.get_data('templates', tmpl).decode())
        with open(outf, 'w') as f:
            log.info(f'Writing template {tmpl} to {outf}')
            f.write(template.render(**kwargs))
    except Exception as e:
        raise Exception(f'Error writing template {tmpl} to {outf}, {e}')



def _add_service(deployment_dir, deployment_name, service_name):
    """ Adds new service templates to given deployment """
    log.info(f'Adding {service_name} to {deployment_dir}/{deployment_name}')
    service_dir = f'{deployment_dir}/{deployment_name}/services/{service_name}'

    if os.path.isdir(service_dir):
        log.warning(f'Service {service_name} already exists at {service_dir}, skipping')
        return

    # Create service directories
    os.makedirs(f'{service_dir}/src')
    os.makedirs(f'{service_dir}/manifests')
    os.makedirs(f'{service_dir}/terraform')
    os.makedirs(f'{service_dir}/terraform/backend')

    write_template('service_makefile.mako', f'{service_dir}/Makefile', service_name=service_name)
    write_template('service_dockerfile.mako', f'{service_dir}/Dockerfile')
    write_template('tf_empty.mako', f'{service_dir}/terraform/input.tf')
    write_template('tf_output.mako', f'{service_dir}/terraform/output.tf', service_name=service_name)
    write_template('tf_service_main.mako', f'{service_dir}/terraform/main.tf', service_name=service_name)
    write_template('service_app.mako', f'{service_dir}/src/main.py')
    write_template('00-manifest.mako', f'{service_dir}/manifests/00-manifest.yaml', service_name=service_name, deployment_name=deployment_name)
    write_template('requirements_txt.mako', f'{service_dir}/src/requirements.txt')
    write_template('tf_service_backend.mako', f'{service_dir}/terraform/backend/test_env_config.tfvars', service=service_name, deployment=deployment_name, env='test')
    write_template('tf_service_backend.mako', f'{service_dir}/terraform/backend/prod_env_config.tfvars', service=service_name, deployment=deployment_name, env='prod')

    manifest_spec = {
        'name': service_name,
        'image': '???',
        'imagePullPolicy': 'Always',
        'ports': [{
            'containerPort': 8000
        }]
    }

    #update deployment manifest with new service
    with open(f'{deployment_dir}/{deployment_name}/manifests/00-deployment.yaml', 'r') as f:
        manifest = yaml.safe_load(f)

    with open(f'{deployment_dir}/{deployment_name}/manifests/00-deployment.yaml', 'w') as f:
        try:
            manifest['spec']['template']['spec']['containers'].append(manifest_spec)
        except:
            manifest['spec']['template']['spec']['containers'] = [manifest_spec]
        yaml.dump(manifest, f, sort_keys=False)


def _add_deployment(deployment_dir, deployment_name):
    """ Adds new deployment directory """
    deployment_path = f'{deployment_dir}/{deployment_name}'
    tf_path = f'{deployment_dir}/terraform'

    if os.path.isdir(deployment_path):
        log.warning(f'Deployment {deployment_name} already exists at {deployment_path}, skipping')
        return

    os.makedirs(f'{deployment_path}/manifests')
    os.makedirs(f'{deployment_path}/services')
    os.makedirs(f'{deployment_path}/terraform')
    os.makedirs(f'{deployment_path}/terraform/backend')

    if not os.path.isfile(f'{deployment_path}/manifests/00-deployment.yaml'):
        write_template('00-deployment.mako', f'{deployment_path}/manifests/00-deployment.yaml', deployment_name=deployment_name)
    if not os.path.isfile(f'{deployment_path}/main.tf'):
        write_template('tf_deployment_main.mako', f'{deployment_path}/terraform/main.tf')
    if not os.path.isfile(f'{deployment_path}/terraform/input.tf'):
        write_template('tf_empty.mako', f'{deployment_path}/terraform/input.tf')
    if not os.path.isfile(f'{deployment_path}/terraform/output.tf'):
        write_template('tf_empty.mako', f'{deployment_path}/terraform/output.tf')

    if not os.path.isfile(f'{deployment_path}/terraform/backend/test_env_config.tfvars'):
        write_template('tf_deployment_backend.mako', f'{deployment_path}/terraform/backend/test_env_config.tfvars', deployment=deployment_name, env='test')
    if not os.path.isfile(f'{deployment_path}/terraform/backend/prod_env_config.tfvars'):
        write_template('tf_deployment_backend.mako', f'{deployment_path}/terraform/backend/prod_env_config.tfvars', deployment=deployment_name, env='prod')
