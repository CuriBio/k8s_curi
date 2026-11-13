# Developer Environment Setup

This guide gets a new developer from a fresh Mac or Windows machine to running the k8s services and the Pulse3D frontend locally. You can run them in either of two ways:

- **Fully local** ([section 9](#9-run-the-stack-fully-locally-no-cluster-access-needed)): the services use a Postgres container on your machine. You don't need cluster access, so this is the quickest way to get a working login.
- **Against a cluster** ([section 10](#10-run-the-stack-against-a-cluster)): the services use a real cluster's database. This needs the access described in section 1.

For day-to-day operational procedures (sealed secrets, Argo, Grafana, Terraform, adding DB migrations, etc.) see the team's **k8s_curi Setup + Development** Google Doc.

> **Windows users:** the repo assumes a POSIX shell (`make`, `source`, `export`-style env files, npm scripts like `NODE_ENV=production ...`). Do everything inside **WSL2 (Ubuntu)**, not PowerShell or Git Bash. Once WSL2 is set up, the Windows instructions are nearly identical to the Mac ones.

---

## 1. Access you need before starting

Ask your lead / whoever administers these for:

- [ ] GitHub access to the `k8s_curi` repo
- [ ] LastPass access, including the **Shared-Curi SW Admin** folder
- [ ] An AWS IAM user (access key + secret) **in each cluster's AWS account**. The `test`, `modl`, and `prod` clusters live in **separate AWS accounts**, so keys for one account will not work for another. Start with `test` and `modl`; most development should not need `prod`.
- [ ] **Kubernetes access on each cluster**, granted separately from the IAM user (see below).

| Cluster | AWS account | Used for |
|---|---|---|
| `test` | `077346344852` | Day-to-day dev. The service `Makefile`s push images here, and the team docs use `ktest` for migrations, DB access, Grafana, etc. |
| `modl` | `725604423866` | Running the local stack against a cluster (section 10) |
| `prod` | `245339368379` | Production. Avoid unless you need it |

**An IAM user alone doesn't give you cluster access.** With only an IAM user, `kubectl` authenticates you but refuses everything:

```
Error from server (Forbidden): namespaces is forbidden: User "arn:aws:iam::<account>:user/<you>" cannot list resource "namespaces" ...
```

On a cluster that doesn't map your account at all, you get `error: You must be logged in to the server (the server has asked for the client to provide credentials)` instead.

To grant cluster access, add your IAM user ARN to `cluster_users` in `cluster/terraform/<cluster>_env.tfvars`:

```hcl
  {
    userarn  = "arn:aws:iam::<account>:user/<you>"
    username = "<you>"
    groups   = ["system:masters"]
  },
```

You can open the PR yourself, but you **can't apply it yourself**. Terraform writes the `aws-auth` ConfigMap using the credentials of whoever runs it, and you don't have cluster access yet. Each cluster gets the change differently (see [How changes reach the clusters](#how-changes-reach-the-clusters)):

| Cluster | How the `cluster_users` change gets applied |
|---|---|
| `prod` | Automatically, when the PR merges into `main` |
| `modl` | Automatically, when a PR merges into `modl-qc`. A PR into `main` doesn't trigger it, so someone with access has to run the modl Terraform workflow in Argo or run `terraform apply` locally |
| `test` | No CI. Someone with access runs `terraform apply -var-file=test_env.tfvars` locally |

If you need access before Terraform runs, an admin can grant it straight away. Use the ARN form of your username, which is what the cluster sees before you're mapped:

```bash
kmodl create clusterrolebinding <you>-admin --clusterrole=cluster-admin \
  --user=arn:aws:iam::725604423866:user/<you>
```

Delete the binding once your `cluster_users` entry is applied.

To check your access, run `kubectl auth whoami`. Before you're mapped, it shows your full ARN as the username and only `system:authenticated`. After, it shows your short username and `system:masters`.

Until you have both, you can still do everything up to section 9 and run the stack fully locally.

---

## 2. Install tools

| Tool | Version | Notes |
|---|---|---|
| Terraform | 1.5.2 | Managed with `tfenv`; a few modules pin 1.5.7 |
| Python | 3.11 | Matches the service Dockerfiles (`python:3.11`) |
| Node | 16 (`^16.17.0`) | Enforced by `frontend/pulse3d/src/check-engines.js`; managed with `nvm` |
| kubectl | 1.30.x | Known working: v1.30.5 |
| Docker + Compose | Docker Desktop | |
| AWS CLI | v2 | |
| kubeseal, jq, psql, make | latest | |

### Mac

1. Install [Homebrew](https://brew.sh) if you don't have it.
2. Install tools:
   ```zsh
   brew install tfenv pyenv awscli kubeseal jq libpq make
   tfenv install 1.5.2 && tfenv use 1.5.2
   pyenv install 3.11 && pyenv global 3.11
   ```
   Follow the `pyenv` post-install instructions to add it to `~/.zshrc`.
3. Install `nvm` ([instructions](https://github.com/nvm-sh/nvm#installing-and-updating)), then:
   ```zsh
   nvm install 16 && nvm alias default 16
   ```
4. Install kubectl v1.30.5 (Homebrew only offers the latest version):
   ```zsh
   # Apple Silicon; use darwin/amd64 on Intel Macs
   curl -LO "https://dl.k8s.io/release/v1.30.5/bin/darwin/arm64/kubectl"
   # verify the download
   echo "$(curl -fsSL https://dl.k8s.io/release/v1.30.5/bin/darwin/arm64/kubectl.sha256)  kubectl" | shasum -a 256 --check
   chmod +x kubectl && mkdir -p ~/.local/bin && mv kubectl ~/.local/bin/kubectl
   ```
   Make sure `~/.local/bin` is on your PATH. On Apple Silicon Macs `/usr/local/bin` often doesn't exist, and using it needs `sudo`.
5. Install [Docker Desktop](https://www.docker.com/products/docker-desktop/). On Apple Silicon, enable **Settings → General → Use Rosetta for x86_64/amd64 emulation**. The local stack builds `linux/amd64` images.
6. `psql` is keg-only. Add it to your PATH in `~/.zshrc`:
   ```zsh
   export PATH="/opt/homebrew/opt/libpq/bin:$PATH"
   ```

### Windows (WSL2)

1. In an **admin PowerShell**, install WSL2 with Ubuntu and reboot:
   ```powershell
   wsl --install -d Ubuntu
   ```
2. Install [Docker Desktop](https://www.docker.com/products/docker-desktop/). In its settings:
   - **General**: enable *Use the WSL 2 based engine*
   - **Resources → WSL Integration**: enable integration for *Ubuntu*
3. Open the **Ubuntu** terminal. Run everything below, and the rest of this guide, there.
4. Install build dependencies:
   ```bash
   sudo apt update && sudo apt install -y build-essential curl git unzip jq make \
     postgresql-client libssl-dev zlib1g-dev libbz2-dev libreadline-dev \
     libsqlite3-dev libffi-dev liblzma-dev tk-dev
   ```
5. Install [Homebrew on Linux](https://docs.brew.sh/Homebrew-on-Linux) (follow its instructions for adding it to `~/.bashrc`), then:
   ```bash
   brew install tfenv pyenv kubeseal
   tfenv install 1.5.2 && tfenv use 1.5.2
   pyenv install 3.11 && pyenv global 3.11
   ```
   Follow the `pyenv` post-install instructions to add it to `~/.bashrc`.
6. Install the AWS CLI v2:
   ```bash
   curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o awscliv2.zip
   unzip awscliv2.zip && sudo ./aws/install && rm -rf aws awscliv2.zip
   ```
7. Install `nvm` ([instructions](https://github.com/nvm-sh/nvm#installing-and-updating)), then:
   ```bash
   nvm install 16 && nvm alias default 16
   ```
8. Install kubectl v1.30.5:
   ```bash
   curl -LO "https://dl.k8s.io/release/v1.30.5/bin/linux/amd64/kubectl"
   sudo install -m 0755 kubectl /usr/local/bin/kubectl && rm kubectl
   ```

**Windows gotchas**

- Clone the repo and keep all config **inside the WSL filesystem** (e.g. `~/workspace`), not under `/mnt/c/...`. It's much faster, and it avoids line-ending problems.
- `docker-compose.yml` mounts `~/.aws` and `~/.kube`. Inside WSL, `~` is your **Linux** home, so your AWS credentials and kubeconfigs must live there, not in `C:\Users\<you>`.
- Set `git config --global core.autocrlf input` so shell scripts keep LF line endings.
- The frontend at `localhost:3000` is reachable from your Windows browser as usual.
- Your shell config file is `~/.bashrc`, not `~/.zshrc`, unless you've switched to zsh.

### Verify installs (both platforms)

```bash
terraform version        # v1.5.2
python --version         # 3.11.x
node --version           # v16.x
kubectl version --client # v1.30.5
aws --version            # aws-cli/2.x
docker compose version
kubeseal --version
psql --version
```

---

## 3. Clone the repo

```bash
mkdir -p ~/workspace && cd ~/workspace
git clone <k8s_curi repo URL>
cd k8s_curi
pip install pre-commit && pre-commit install
```

---

## 4. Configure AWS profiles

Profiles **must** be named `curi_<cluster>`. The kubeconfigs and `docker-compose.yml` assume this, for example `~/.kube/${AWS_PROFILE}_config`.

For each account you have keys for:

```bash
aws configure --profile curi_test   # region: us-east-2, output: json
aws configure --profile curi_modl
aws configure --profile curi_prod   # only if you have prod access
```

Each profile must use the key from **that** account. Check that each one resolves to the expected account ID from the table in section 1:

```bash
for p in curi_test curi_modl curi_prod; do AWS_PROFILE=$p aws sts get-caller-identity --query Arn --output text; done
```

If two profiles show the same account, you've used one account's key for both.

If your access is through a role rather than an IAM user per account, add the profile to `~/.aws/config` by hand instead:

```ini
[profile curi_test]
role_arn = arn:aws:iam::<test-account-id>:role/<role-name>
source_profile = <profile with your base keys>
region = us-east-2
```

---

## 5. Download kubeconfigs

Each cluster's kubeconfig is in that account's Terraform state bucket:

```bash
mkdir -p ~/.kube
AWS_PROFILE=curi_test aws s3 cp s3://curi-eks-test-cluster-tf-state/curi_test_config ~/.kube/
AWS_PROFILE=curi_modl aws s3 cp s3://curi-eks-modl-cluster-tf-state/curi_modl_config ~/.kube/
AWS_PROFILE=curi_prod aws s3 cp s3://curi-eks-prod-cluster-tf-state/curi_prod_config ~/.kube/
```

`AccessDenied ... no resource-based policy allows` means you don't have access to that cluster's AWS account yet. See section 1.

The S3 copies aren't always current. If `kubectl` fails with `x509: certificate signed by unknown authority` or `no such host`, generate the kubeconfig from EKS instead. Cluster names are in `cluster_name` in each `<cluster>_env.tfvars`, for example `modl-v2` and `prod-v2`:

```bash
AWS_PROFILE=curi_modl aws eks update-kubeconfig --region us-east-2 --name modl-v2 \
  --kubeconfig ~/.kube/curi_modl_config
```

Always pass `--kubeconfig`. Without it, `update-kubeconfig` writes to `~/.kube/config` and switches your default context to the cluster you just added. If the last cluster you added was prod, a bare `kubectl` command then runs against **prod**. The `k<cluster>` aliases (section 7) aren't affected, since they use their own files.

---

## 6. Environment files

1. From LastPass, download the env file for each cluster (`.env_test`, `.env_modl`, `.env_prod`).
2. Store them **outside the repo** so they can't be committed:
   ```bash
   mkdir -p ~/.config/k8s_curi
   # save as ~/.config/k8s_curi/.env_test, etc.
   ```
3. In each file:
   - Set `CODE_ARTIFACT_ACCESS_KEY_ID` and `CODE_ARTIFACT_ACCESS_KEY` to your personal AWS access key. These are only used to pull packages from CodeArtifact during Docker builds.
     - In `.env_modl` and `.env_prod`, use your key for that account.
     - In `.env_test`, use your **modl** key. The test account has no CodeArtifact, so `CODE_ARTIFACT_ACCOUNT_ID` in that file points at modl.
   - Check that `AWS_PROFILE` matches that cluster's profile name (e.g. `curi_test`)

These values don't configure your AWS profiles (section 4). The `curi_test` profile still needs a key from the test account itself.

---

## 7. Shell aliases

The team docs use `ktest` / `kmodl` / `kprod` everywhere. Add these to `~/.zshrc` (Mac) or `~/.bashrc` (WSL), then open a new terminal:

```bash
alias ktest="AWS_PROFILE=curi_test kubectl --kubeconfig ~/.kube/curi_test_config"
alias kmodl="AWS_PROFILE=curi_modl kubectl --kubeconfig ~/.kube/curi_modl_config"
alias kprod="AWS_PROFILE=curi_prod kubectl --kubeconfig ~/.kube/curi_prod_config"
```

Verify cluster access:

```bash
ktest get pods -A
```

If this returns `Forbidden`, your IAM user works but you haven't been granted cluster access yet (see section 1).

---

## 8. Frontend dependencies

```bash
cd frontend/pulse3d/src
nvm use 16
npm i
```

---

## 9. Run the stack fully locally (no cluster access needed)

`docker-compose.local.yml` layers on top of `docker-compose.yml` and makes these changes:

- Adds a **Postgres 17** container (the same major version as RDS).
- Runs every alembic migration in `core/db/curibio` against it, which builds the full schema and the per-service DB roles.
- Seeds a local admin account (`bin/local_db_seed.sql`).
- Points the five backend APIs at that database instead of the cluster's.
- Disables the `psql-proxy` container.

All settings come from `local.env` in the repo root. Every value in it is a dummy, so it's safe to commit. The database starts **empty**: it has the same schema as the cluster databases but none of their data.

Add this alias (you'll use it a lot):

```bash
alias dclocal='docker compose -f docker-compose.yml -f docker-compose.local.yml --env-file local.env'
```

**Terminal 1**: build and start the backend

```bash
# the pulse3d build needs CodeArtifact credentials, so pass your cluster env file for the build only
docker compose --env-file ~/.config/k8s_curi/.env_modl build
dclocal up
```

Wait until each API logs `Application startup complete.` The `db-migrate` and `db-seed` containers are expected to exit with code 0 after they finish. They re-run on every `up` and are safe to repeat.

**Terminal 2**: start the frontend

```bash
cd frontend/pulse3d/src
npm run dev
```

**Browser**: open <http://localhost:3000/login> and use the **admin** login with `admin@example.com` / `local-admin-pass`. As `curi:admin` you can create customers and users from the UI.

Useful commands:

```bash
dclocal down                          # stop, keeping the data
dclocal down -v                       # wipe the DB; the next `up` rebuilds it from the migrations
psql -h localhost -U root curibio     # password: local-root-pass
```

**What doesn't work locally:**

- **S3 uploads/downloads** still go to real AWS buckets, so they need credentials for the right account.
- **Analyses don't run**, because the workers in `jobs/` aren't part of the compose stack.
- **Email and Microsoft SSO** use dummy values, so they're disabled.

**Notes for editing `local.env`:**

- Don't use `.test`, `.local`, or similar reserved domains in the email values. The email validation in the APIs rejects them, and the services crash on startup.
- The admin account is created when the DB is first built. If you change `CURIBIO_CUSTOMER_LOGIN` or `CURIBIO_CUSTOMER_PASS`, run `dclocal down -v` to rebuild it.

---

## 10. Run the stack against a cluster

This needs Kubernetes access to the cluster (section 1). Use **modl**.

> Running the local stack connects to that cluster's **real database**. Never point it at `prod` casually: anything you create or upload locally is real data. The `psql-proxy` container also creates a `psql-proxy` pod in the cluster if one isn't running.

You don't need a separate `kmodl port-forward`. The `psql-proxy` container in `docker-compose.yml` uses your mounted `~/.aws` and `~/.kube` to forward the cluster database to host port 5432. Running your own port-forward as well makes `up` fail, because port 5432 is already taken.

**Terminal 1**: build and start the backend services

```bash
docker compose --env-file ~/.config/k8s_curi/.env_modl build   # check for build errors
docker compose --env-file ~/.config/k8s_curi/.env_modl up      # check all containers start
```

Then check that every API logged `Application startup complete`. `depends_on` only waits for the `psql-proxy` container to start, not for its port-forward to be ready. So on a cold start, the APIs that connect to the database straight away (`apiv2-users`, `apiv2-mantarray`, `apiv2-event-broker`) can fail with `ConnectionError: unexpected connection_lost()` and stop. Their containers still show as running. Restart them once the proxy logs `Forwarding from 0.0.0.0:5432`:

```bash
docker compose --env-file ~/.config/k8s_curi/.env_modl restart apiv2-users apiv2-mantarray apiv2-event-broker
```

`Error from server (AlreadyExists): pods "psql-proxy" already exists` in the `psql-proxy` logs is harmless. The pod is already running in the cluster, and the container forwards to it.

To use `psql` against the cluster database while the stack is running:

```bash
source ~/.config/k8s_curi/.env_modl
PGPASSWORD=$POSTGRES_PASSWORD psql -d curibio -U root -h localhost
```

This is `root` on the shared modl database, so stick to read-only queries unless you mean to change data. To use `psql` without the compose stack, run `kmodl port-forward svc/psql-proxy 5432:5432` instead.

**Terminal 2**: start the frontend

```bash
cd frontend/pulse3d/src
npm run dev
```

**Browser**: open <http://localhost:3000/login>.

- If you already have an account, log in.
- If not, log in with the **Curi Admin - Modl** credentials (LastPass, *Shared-Curi SW Admin* folder) and create a profile for yourself.

---

## How changes reach the clusters

CI runs as Argo Workflows inside each cluster, triggered by GitHub PR events. Argo CD also syncs some manifests from git.

| Cluster | Trigger | What runs |
|---|---|---|
| `prod` | PR opened against `main` | Build check, plus `terraform plan` if `cluster/terraform` changed |
| `prod` | PR merged into `main` | UI upload, `alembic upgrade head` on the prod DB, image build and push to prod ECR, and `terraform apply -auto-approve` if `cluster/terraform` changed. **This changes prod with no approval step.** |
| `modl` | PR opened against / merged into `modl-qc` | The same as prod, against modl |
| `test` | None | Nothing. Changes are applied by hand |

The usual flow is feature branch → `modl-qc` → a "Release RC" PR from `modl-qc` into `main`. Changes that don't touch the apps or services, such as `cluster_users`, can go straight to `main`, but then they don't reach modl until `main` is next merged into `modl-qc`.

**Service deployments aren't automatic.** CI pushes new images, but the manifests under `deployments/*/manifests` are applied by hand (`k<cluster> apply -k <path>/manifests/overlays/<cluster>`). Argo CD auto-syncs only the CI tooling: argo-events, argo-workflows and the CI templates (`cluster/manifests/apps_<cluster>.yaml`). For prod and test it tracks `main`; for modl it tracks `modl-qc`.

To see CI runs, connect to Argo. This needs cluster access, and it's only reachable through a port-forward:

```bash
# Argo Workflows: copies the login token to your clipboard, then forwards the UI to https://localhost:2746
echo -n "Bearer $(kmodl -n argo get secret argo-server.service-account-token -o jsonpath='{.data.token}' | base64 --decode)" | pbcopy
kmodl -n argo port-forward deployment/argo-server 2746:2746

# Argo CD: https://localhost:8080
kmodl port-forward svc/argocd-server -n argocd 8080:443
```

The CI pipelines don't always post a status back to the PR. If you need to know whether a merge applied, check for the workflow run in Argo Workflows.

---

## 11. Smoke test: DB migrations (alembic)

This uses the **test** cluster, so it needs `test` access. To try a new migration without any cluster access, run `dclocal up` (section 9). That applies all migrations to your local DB.

**Terminal 1**

```bash
ktest port-forward svc/psql-proxy 5432:5432
```

**Terminal 2**

```bash
cd core/db/curibio
python -m venv venv-alembic
. venv-alembic/bin/activate
pip install -r requirements.txt
source ~/.config/k8s_curi/.env_test
alembic current
```

Output like `<hex-string> (head)` means the setup works. Don't run `alembic upgrade head` unless you're actually applying a migration.

---

## 12. Running service unit tests

Most services under `deployments/` have pytest suites. The frontend and `jobs/` have none, and the Playwright suite in `e2e/` is unmaintained.

Example for the users service:

```bash
cd deployments/apiv2/services/users
python3.11 -m venv venv-apiv2-users
. venv-apiv2-users/bin/activate
pip install -r tests/requirements-dev.txt
pip install -r src/requirements.txt
```

Open the service's `Dockerfile` and find the `pip install ./lib/<lib>` lines. Install each of those core libs in editable mode:

```bash
pip install -e ../../../../core/lib/auth
pip install -e ../../../../core/lib/utils
# ...one per lib listed in the Dockerfile
pytest
```

Some failures may come from outdated tests rather than a broken setup. Read the error messages before assuming your environment is wrong.

---

## Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| `kubectl` errors about credentials or `exec plugin` | The AWS CLI isn't installed, or the profile named in the kubeconfig (`curi_<cluster>`) doesn't exist |
| `AccessDenied` on an S3 bucket or cluster | Your keys are for a different AWS account. Each cluster has its own account |
| `kubectl` returns `Forbidden ... cannot list resource` | Your IAM user works but has no Kubernetes access on that cluster. See section 1 |
| `kubectl` says `the server has asked for the client to provide credentials` | The cluster doesn't map your account at all. Check that you're using the right profile for that cluster's account, then see section 1 |
| `kubectl` fails with `x509: certificate signed by unknown authority` or `no such host` | Your kubeconfig is out of date, or the cluster was rebuilt. Regenerate it with `aws eks update-kubeconfig` (section 5) |
| A bare `kubectl` command hits the wrong cluster | `aws eks update-kubeconfig` without `--kubeconfig` changed your default context. Check `kubectl config current-context`, or use the `k<cluster>` aliases |
| UI login shows *"Internal error. Please try again later."* | The users API can't reach a database. Check `docker compose logs apiv2-users`. Against a cluster, it's usually the startup race in section 10: restart the APIs. Otherwise, fix your cluster access or use the fully local stack (section 9) |
| `up` fails with `failed to set up container networking: network <id> not found` | The containers are attached to a Docker network that no longer exists, for example after a Docker Desktop reset or a `docker network prune`. Run `up --force-recreate --remove-orphans` |
| `up` warns `Found orphan containers (... postgres, db-migrate, db-seed)` | They're left over from the fully local stack. Add `--remove-orphans`, or run `dclocal down` first |
| Local admin login returns 500, and the logs say `Tokens must have at least 1 scope` | The admin account is missing its `curi:admin` scope. Run `dclocal up` so `db-seed` re-runs, and check that `CURIBIO_CUSTOMER_LOGIN` matches the account in the DB |
| A local API crashes on startup with `MAIL_FROM value is not a valid email address` | An email in `local.env` uses a reserved domain such as `.test`. Use `example.com` |
| `npm run dev` fails an engines check | Wrong Node version. Run `nvm use 16` |
| Docker builds fail with cryptic errors | Run `docker system prune` to clear cached images and try again |
| `psql: command not found` (Mac) | Add the `libpq` PATH line from section 2 |
| Compose can't find AWS/kube config (Windows) | Config is in your Windows home instead of your WSL home |
| Port 5432 already in use | A local Postgres, a `kmodl port-forward` left running, or the `psql-proxy` / local `postgres` container is using it. Stop whichever you don't need (e.g. `dclocal down` before switching to the cluster stack). `lsof -nP -iTCP:5432 -sTCP:LISTEN` shows what's using it |
