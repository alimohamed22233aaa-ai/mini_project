# Mini Project: DevOps Delivery Challenge

A Python Flask API that is built, tested, scanned, containerised and deployed to an AWS EC2 instance.
The whole flow is automated: **Git → GitHub Actions → SonarQube → Docker image (GHCR) → EC2 → smoke test**.
The infrastructure is created with **Terraform** and the server is configured with **Ansible**.

## Tech stack

| Area | Tool |
|---|---|
| Application | Python 3.12, Flask 3.0.3 |
| Tests | pytest, pytest-cov |
| Containers | Docker, Docker Compose |
| Infrastructure | Terraform (AWS provider ~> 6.0) |
| Configuration | Ansible (single playbook) |
| CI/CD | GitHub Actions |
| Code quality | SonarQube Community (self-hosted on the EC2 instance) |
| Registry | GitHub Container Registry (GHCR) |

## API endpoints

| Method | Path | Response |
|---|---|---|
| GET | `/health` | `200` with `{"status": "ok"}` |
| GET | `/` | `200` with JSON `{"app": "web-app", "version": "<sha>"}`; browsers (`Accept: text/html`) get an HTML landing page that shows the version and health status |

The version is the 7-character commit SHA. It is injected at build time (`APP_VERSION` build argument), so the running version always tells you which image is deployed.

## Repository layout

```
.
├── .github/workflows/
│   ├── deployment.yml                 # CI/CD pipeline
│   └── rollback.yml                   # manual rollback to a previous image tag
├── ansible/
│   ├── ansible.cfg
│   ├── inventory.ini                  # target host + SSH key
│   └── playbook.yml                   # Docker + Compose + SonarQube bootstrap
├── app/
│   ├── app.py                         # Flask application
│   ├── Dockerfile                     # slim image, non-root user, healthcheck
│   ├── docker-compose.yml             # runs the published image
│   ├── requirements.txt
│   └── .dockerignore
├── infra/
│   ├── modules/ec2/                   # VPC, subnet, IGW, SG, EC2 instance
│   └── dev/                           # dev environment using the module
├── tests/test_app.py                  # pytest tests
├── sonar-project.properties
└── README.md
```

## Architecture

```
git push
   │
   ▼
GitHub Actions
   ├─ Unit_Test       pytest + coverage report
   ├─ SonarQube_Scan  analysis against SonarQube running on EC2
   ├─ Build           docker build + push to GHCR, tag = first 7 chars of commit SHA
   └─ Deploy          self-hosted runner on EC2: docker compose pull && up -d, then /health smoke test
```

Each stage depends on the previous one (`needs`), so a failed test or scan stops the pipeline before any image is built.
`Build` and `Deploy` run only on pushes to `main`. Pull requests run tests and the scan only.

**Fail closed:** if SonarQube is unavailable, the scan job fails, and because `Build` needs it, no image is built and nothing is released.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r app/requirements.txt
pip install pytest pytest-cov

python -m pytest -v                # run from the repository root
python app/app.py                  # http://localhost:5000
```

Quick check:

```bash
curl http://localhost:5000/health
# {"status":"ok"}
curl http://localhost:5000/
# {"app":"web-app","version":"dev"}
```

On Windows PowerShell use `curl.exe` instead of `curl`.

## Tests

`tests/test_app.py` covers:

| Test | Checks |
|---|---|
| `test_health` | `/health` returns `200` and `{"status": "ok"}` |
| `test_index_returns_json_with_version` | `/` returns JSON with `app` and `version` |
| `test_index_returns_html_for_browser` | `/` with `Accept: text/html` returns the HTML page |

## Run with Docker

Build and run the image from the repository root. Pass a version so the app can report it:

```bash
docker build --build-arg APP_VERSION=local -t web-app ./app
docker run -d -p 5000:5000 --name flask-app web-app
curl http://localhost:5000/
# {"app":"web-app","version":"local"}
```

In the Dockerfile, `ARG APP_VERSION` receives the value at build time and `ENV APP_VERSION=${APP_VERSION}` keeps it in the image so the app can read it at runtime.

The Compose file runs the **published** image from GHCR, so it needs two variables:

```bash
cd app
export IMAGE_NAME=ghcr.io/<github-owner-lowercase>/web-app
export IMAGE_TAG=<7-char-commit-sha>
docker compose pull
docker compose up -d
docker compose ps        # STATUS should become "healthy"
```

In `docker-compose.yml` the image is referenced as `${IMAGE_NAME}:${IMAGE_TAG}`.
If the package is private, log in first: `echo <PAT> | docker login ghcr.io -u <github-user> --password-stdin` (the PAT needs `read:packages`).

The image runs as a non-root user and the Compose service defines a healthcheck that calls `/health`.

## Infrastructure with Terraform

Prerequisites: Terraform, AWS CLI with a configured profile (the dev environment uses the profile `aliprofile`), and an existing EC2 key pair named `depi-key`.

Create `infra/dev/terraform.tfvars` (it is git-ignored and must never be committed):

```hcl
vpc_cidr      = "10.0.0.0/16"
subnet_cidr   = "10.0.1.0/24"
instance_name = "depi-server"
sg-name       = "depi-sg"
my_ip         = "<your-public-ip>/32"
```

Then run:

```bash
cd infra/dev
terraform init
terraform fmt -recursive
terraform validate
terraform plan
terraform apply
```

The output `instance_public_ip` is the address of the new server.

What gets created: VPC, public subnet, internet gateway, route table, security group, and one Ubuntu 24.04 EC2 instance (AMI found with a `data` source). On first boot, `user_data` prepares a SonarQube + PostgreSQL Compose file in `/sonar-lab`.

### Security group

| Port | Purpose | Allowed from |
|---|---|---|
| 22 | SSH | `my_ip` only |
| 5000 | Flask app | `my_ip` only |
| 9000 | SonarQube | open, see [Known limitations](#known-limitations) |

## Server configuration with Ansible

The configuration is a single playbook (tasks, variables and handlers, no separate roles).

1. Put the instance IP from the Terraform output into `ansible/inventory.ini`.
2. Make sure the key file path in the inventory points to your `.pem` key.
3. Run:

```bash
cd ansible
ansible-playbook playbook.yml
```

The playbook installs Docker Engine and the Compose plugin from Docker's official APT repository, enables the Docker service, adds the SSH user to the `docker` group, creates `/opt/app` and starts SonarQube from `/sonar-lab`. Docker changes use a handler that restarts the service only when needed.

### Idempotency check

Run the playbook twice. The second run must report no changes:

```bash
ansible-playbook playbook.yml     # first run: changes applied
ansible-playbook playbook.yml     # second run: expect changed=0 in the PLAY RECAP
```

## CI/CD pipeline

Workflow file: `.github/workflows/deployment.yml`

| Job | What it does |
|---|---|
| `Unit_Test` | installs dependencies, runs pytest with coverage, uploads `python-coverage.xml` |
| `SonarQube_Scan` | downloads the coverage report and runs the SonarQube scan |
| `Build` | logs in to GHCR with `GITHUB_TOKEN`, builds `./app` with `APP_VERSION=<short-sha>`, pushes `ghcr.io/<owner>/web-app:<short-sha>` |
| `Deploy` | runs on the self-hosted runner installed on the EC2 instance, logs in to GHCR, recreates the service with the new tag, then runs the smoke test |

The `Build` job exposes the image name and the short tag as job outputs. `Deploy` passes them to Docker Compose as `IMAGE_NAME` and `IMAGE_TAG`, and uses `./app` as the default working directory.

### Smoke test

After `docker compose up -d`, the `Deploy` job calls `http://localhost:5000/health` up to 15 times, 4 seconds apart. If it never returns `200`, the job prints `docker compose ps` and the last 50 log lines and fails, so a broken release turns the pipeline red instead of looking successful.

### Required GitHub settings

| Name | Type | Used for |
|---|---|---|
| `SONAR_TOKEN` | secret | SonarQube authentication |
| `SONAR_HOST_URL` | secret | SonarQube URL, `http://<ec2-ip>:9000` |
| `GITHUB_TOKEN` | automatic | GHCR login (no setup needed) |

No Docker Hub credentials are needed. The `Build` job has `packages: write` permission to push, and `Deploy` only needs `packages: read`.

### Why the deploy job uses a self-hosted runner

The security group allows SSH only from my own IP address. GitHub-hosted runners come from changing IP ranges, so they cannot reach port 22 on the server, and deploying over SSH with a stored key failed for that reason.

Instead of opening SSH to the whole internet, a GitHub Actions runner is installed **on the EC2 instance itself**. It connects outbound to GitHub, so no inbound SSH rule is needed and port 22 stays restricted. This also follows the advice to avoid long-lived SSH keys in CI. The key-based approach is still possible (for example by opening port 22 temporarily to the runner IP, or by using AWS SSM), but it trades away the restricted SSH rule.

## Failure simulation

To demonstrate a failed rollout, make `/health` return an error on purpose:

```python
@app.route("/health", methods=["GET"])
def health():
    return jsonify(status="error"), 500
```

(The unit test for `/health` fails first. For the demo, push the change in a branch where that test is adjusted, or temporarily skip it.)

Expected result: the image is built and deployed, the smoke test fails after about a minute, the `Deploy` job turns red and prints the container status and logs. The running version at `/` shows the broken SHA.

## Rollback

Every image is tagged with the commit SHA, so a previous known-good version is always available in GHCR. Rolling back means running that older tag. It does not rebuild anything.

### Option 1: GitHub Actions (recommended)

1. Go to **Actions → Rollback → Run workflow**.
2. Enter the previous known-good tag (7-char SHA).
3. The workflow pulls that image, recreates the service on the EC2 runner and runs the same `/health` smoke test.

Workflow file: `.github/workflows/rollback.yml` (`workflow_dispatch` with an `image_tag` input).

### Option 2: Manually on the EC2 instance

```bash
cd <runner-work-dir>/mini_project/mini_project/app
export IMAGE_NAME=ghcr.io/<github-owner-lowercase>/web-app
export IMAGE_TAG=<previous-known-good-sha>
docker compose pull
docker compose up -d
curl http://localhost:5000/
```

### Finding the previous good tag

```bash
git log --oneline -5                  # first column is the short SHA
git rev-parse HEAD~1 | cut -c1-7      # the commit before the current one
```

You can also check the successful runs in the GitHub Actions tab or the package versions in the repository's **Packages** section. The image only exists if that commit passed the tests and the scan, so pick a tag from a green run.

### After the rollback

The rollback only changes what is running on the server. `main` still contains the faulty commit, so the next push would deploy it again. Fix the code permanently:

```bash
git revert <faulty-commit-sha>
git push origin main
```

`git revert` adds a new commit that undoes the change and keeps the history intact. The pipeline then builds and deploys the corrected version.

| | Rollback by tag | `git revert` |
|---|---|---|
| Speed | about a minute | full pipeline |
| Goes through tests and scan | no (image already built) | yes |
| Fixes `main` | no | yes |
| Use for | emergency recovery | permanent fix |

## Cleanup

Destroy the AWS resources when you are done to avoid charges:

```bash
cd infra/dev
terraform destroy
```

## Security notes

- `terraform.tfvars`, `*.tfstate`, `*.pem`, `.terraform/` and caches are listed in `.gitignore`.
- No credentials are stored in the repository. The registry login uses the short-lived `GITHUB_TOKEN`, and the SonarQube values live in GitHub secrets.
- Job permissions are limited per job (`packages: write` only where an image is pushed).
- The container runs as a non-root user.
- SSH (22) and the app port (5000) are restricted to a single IP.

## Known limitations

- Port 9000 (SonarQube) is open to the internet so the GitHub-hosted scan job can reach it. Restricting it would require running the scan on the self-hosted runner.
- Deployment uses Docker Compose on the self-hosted runner rather than Ansible, to avoid exposing SSH.
- Terraform state is local (no remote backend).