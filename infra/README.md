# infra

Terraform manages the GCP side only: Cloud Run, Artifact Registry, the runtime
service account, and Secret Manager entries. Supabase (Postgres + pgvector) is
provisioned by hand -- its Terraform provider is thin/community-maintained and buys
little for one small instance. Run `schema.sql` once in the Supabase SQL editor after
creating the project.

## Bootstrap (one-time, before the first `terraform apply`)

1. Create the GCS bucket for remote state:
   ```bash
   gcloud storage buckets create gs://inquilino-ia-tfstate --project=inquilino-ia --location=southamerica-east1
   ```
2. `terraform init`
3. Put the Gemini API key and Supabase connection string into `terraform.tfvars`
   (git-ignored) or pass them as `-var` flags -- never commit them.
4. `terraform plan`, then `terraform apply`. First apply uses the placeholder
   `hello` image since no image has been pushed by CI yet.

## GitHub Actions -> GCP auth (Workload Identity Federation, one-time)

CI authenticates via WIF, not a long-lived service account key:

```bash
gcloud iam workload-identity-pools create github --project=inquilino-ia \
  --location=global --display-name="GitHub Actions"

gcloud iam workload-identity-pools providers create-oidc github \
  --project=inquilino-ia --location=global --workload-identity-pool=github \
  --display-name="GitHub" --issuer-uri="https://token.actions.githubusercontent.com" \
  --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository" \
  --attribute-condition="assertion.repository=='<github-user>/inquilino-ia'"

gcloud iam service-accounts create gha-deployer --project=inquilino-ia

for role in roles/run.admin roles/artifactregistry.admin roles/secretmanager.admin \
            roles/iam.serviceAccountAdmin roles/iam.serviceAccountUser \
            roles/serviceusage.serviceUsageAdmin; do
  gcloud projects add-iam-policy-binding inquilino-ia \
    --member="serviceAccount:gha-deployer@inquilino-ia.iam.gserviceaccount.com" \
    --role="$role"
done

gcloud iam service-accounts add-iam-policy-binding \
  gha-deployer@inquilino-ia.iam.gserviceaccount.com \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/<project-number>/locations/global/workloadIdentityPools/github/attribute.repository/<github-user>/inquilino-ia"
```

Then set repo secrets `WIF_PROVIDER` (full provider resource name),
`WIF_SERVICE_ACCOUNT` (`gha-deployer@inquilino-ia.iam.gserviceaccount.com`),
`GEMINI_API_KEY`, and `SUPABASE_DB_URL`.

## Layout

- `main.tf` -- provider, backend, API enablement
- `variables.tf` -- inputs (project id, region, secrets)
- `secrets.tf` -- Secret Manager entries for GEMINI_API_KEY and SUPABASE_DB_URL
- `cloud_run.tf` -- Artifact Registry repo, runtime service account, Cloud Run v2 service
- `outputs.tf` -- the deployed service URL
