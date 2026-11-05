
## Milestone 6: Observe and Automate

- Live app: https://8-233-65-8.sslip.io
- Deployment branch: `main`
- Successful deploy: commit `18a063dd7b1fbfb3b5d5a369d371c502290044e4` (`18a063d`), built, deployed and health-checked
- Failed deploy and rollback: commit `e4e5db5b6ca38d7a9d94729f23299c091a15abb9` (`e4e5db5`), with `[simulate-failure]` in the message
- Workflow: `.github/workflows/deploy.yml`
- Terraform: `referraldesk/terraform/` (monitoring.tf, cluster.tf, database.tf, infrastructure.tf, pipeline.tf)
- Log-based metrics: `referraldesk_http_5xx` and `referraldesk_http_requests` (defined in `monitoring.tf`)

### Terraform exceptions
- Secret value (the Secret Manager secret exists in Terraform; its value is never stored in code or state)
- Kubernetes workloads, Ingress and managed certificate (managed with kubectl and the pipeline)
- The Terraform state bucket
- The legacy VM and firewall rule

### Pipeline
Push to `main` triggers build, push (image tagged with commit SHA), deploy, health check and automatic rollback on failure.
