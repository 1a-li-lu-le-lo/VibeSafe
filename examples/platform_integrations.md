# VibeSafe Platform Integration Examples

This document provides detailed examples of integrating VibeSafe with popular platforms and services.

## Table of Contents

- [Cloud Platforms](#cloud-platforms)
  - [AWS](#aws)
  - [Google Cloud](#google-cloud)
  - [Azure](#azure)
- [Deployment Platforms](#deployment-platforms)
  - [Vercel](#vercel)
  - [Netlify](#netlify)
  - [Railway](#railway)
- [Container Platforms](#container-platforms)
  - [Kubernetes](#kubernetes)
  - [Docker Compose](#docker-compose)
- [CI/CD Platforms](#cicd-platforms)
  - [GitHub Actions](#github-actions)
  - [GitLab CI](#gitlab-ci)
  - [CircleCI](#circleci)
- [Development Tools](#development-tools)
  - [VS Code](#vs-code)
  - [JetBrains IDEs](#jetbrains-ides)

## Cloud Platforms

### AWS

#### AWS CLI Configuration
```bash
# Set AWS credentials
export AWS_ACCESS_KEY_ID=$(vibesafe get AWS_ACCESS_KEY_ID)
export AWS_SECRET_ACCESS_KEY=$(vibesafe get AWS_SECRET_ACCESS_KEY)
export AWS_SESSION_TOKEN=$(vibesafe get AWS_SESSION_TOKEN)  # If using temporary credentials

# Or create credentials file
mkdir -p ~/.aws
cat > ~/.aws/credentials << EOF
[default]
aws_access_key_id = $(vibesafe get AWS_ACCESS_KEY_ID)
aws_secret_access_key = $(vibesafe get AWS_SECRET_ACCESS_KEY)
EOF
chmod 600 ~/.aws/credentials
```

#### AWS Lambda Secrets
```bash
# Set Lambda environment variables
aws lambda update-function-configuration \
  --function-name my-function \
  --environment Variables="{
    API_KEY=$(vibesafe get API_KEY),
    DB_PASSWORD=$(vibesafe get DB_PASSWORD)
  }"
```

#### AWS Secrets Manager
```bash
# Create secret in AWS Secrets Manager
aws secretsmanager create-secret \
  --name prod/myapp/api-key \
  --secret-string "$(vibesafe get API_KEY)"
```

### Google Cloud

#### gcloud Authentication
```bash
# Create service account key file
vibesafe get GCP_SERVICE_ACCOUNT_KEY > /tmp/gcp-key.json
export GOOGLE_APPLICATION_CREDENTIALS=/tmp/gcp-key.json

# Authenticate
gcloud auth activate-service-account --key-file=/tmp/gcp-key.json

# Clean up
rm /tmp/gcp-key.json
```

#### Google Cloud Functions
```bash
# Deploy with secrets
gcloud functions deploy my-function \
  --set-env-vars API_KEY=$(vibesafe get API_KEY) \
  --set-env-vars DB_URL=$(vibesafe get DB_URL)
```

### Azure

#### Azure CLI Authentication
```bash
# Service principal authentication
az login --service-principal \
  --username $(vibesafe get AZURE_CLIENT_ID) \
  --password $(vibesafe get AZURE_CLIENT_SECRET) \
  --tenant $(vibesafe get AZURE_TENANT_ID)
```

#### Azure Key Vault
```bash
# Add secret to Key Vault
az keyvault secret set \
  --vault-name MyKeyVault \
  --name api-key \
  --value "$(vibesafe get API_KEY)"
```

## Deployment Platforms

### Vercel

#### Environment Variables
```bash
# Set production secrets
vercel env add API_KEY production < <(vibesafe get API_KEY)
vercel env add DATABASE_URL production < <(vibesafe get DATABASE_URL)

# Or use Vercel CLI with pipe
echo "$(vibesafe get API_KEY)" | vercel env add API_KEY production
```

#### Deployment
```bash
# Deploy with secrets
VERCEL_TOKEN=$(vibesafe get VERCEL_TOKEN) vercel --prod
```

### Netlify

#### Environment Variables
```bash
# Using Netlify CLI
echo "$(vibesafe get API_KEY)" | netlify env:set API_KEY

# Multiple secrets
for var in API_KEY DATABASE_URL STRIPE_KEY; do
  echo "$(vibesafe get $var)" | netlify env:set $var
done
```

### Railway

#### Railway CLI
```bash
# Set environment variables
railway variables set API_KEY=$(vibesafe get API_KEY)
railway variables set DATABASE_URL=$(vibesafe get DATABASE_URL)

# Deploy with token
RAILWAY_TOKEN=$(vibesafe get RAILWAY_TOKEN) railway up
```

## Container Platforms

### Kubernetes

#### Creating Secrets
```bash
# Create Kubernetes secret
kubectl create secret generic api-secrets \
  --from-literal=api-key=$(vibesafe get API_KEY) \
  --from-literal=db-password=$(vibesafe get DB_PASSWORD)
```

#### Sealed Secrets
```bash
# Create sealed secret with kubeseal
echo -n $(vibesafe get API_KEY) | kubectl create secret generic api-key \
  --dry-run=client \
  --from-literal=key=/dev/stdin \
  -o yaml | kubeseal -o yaml > sealed-secret.yaml
```

### Docker Compose

#### .env File Generation
```bash
# Generate .env file (be careful - add to .gitignore!)
cat > .env << EOF
API_KEY=$(vibesafe get API_KEY)
DB_PASSWORD=$(vibesafe get DB_PASSWORD)
REDIS_PASSWORD=$(vibesafe get REDIS_PASSWORD)
EOF

# Use in docker-compose
docker-compose up
```

#### Docker Secrets
```bash
# Create Docker secrets
echo "$(vibesafe get DB_PASSWORD)" | docker secret create db_password -
echo "$(vibesafe get API_KEY)" | docker secret create api_key -
```

## CI/CD Platforms

### GitHub Actions

#### Setting Repository Secrets
```bash
# Using GitHub CLI
vibesafe get NPM_TOKEN | gh secret set NPM_TOKEN
vibesafe get DOCKER_PASSWORD | gh secret set DOCKER_PASSWORD

# Multiple secrets
for secret in API_KEY DATABASE_URL SENTRY_DSN; do
  vibesafe get $secret | gh secret set $secret
done
```

#### Workflow Example
```yaml
# .github/workflows/deploy.yml
name: Deploy
on: push

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Deploy to production
        env:
          API_KEY: ${{ secrets.API_KEY }}
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
        run: |
          # Your deployment script
          ./deploy.sh
```

### GitLab CI

#### CI/CD Variables
```bash
# Set project variables using GitLab API
GITLAB_TOKEN=$(vibesafe get GITLAB_TOKEN)
PROJECT_ID="your-project-id"

curl --request POST \
  --header "PRIVATE-TOKEN: $GITLAB_TOKEN" \
  --form "key=API_KEY" \
  --form "value=$(vibesafe get API_KEY)" \
  --form "protected=true" \
  --form "masked=true" \
  "https://gitlab.com/api/v4/projects/$PROJECT_ID/variables"
```

### CircleCI

#### Environment Variables
```bash
# Using CircleCI CLI
circleci env var set API_KEY $(vibesafe get API_KEY)
circleci env var set DATABASE_URL $(vibesafe get DATABASE_URL)
```

## Development Tools

### VS Code

#### tasks.json with Secrets
```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Run with secrets",
      "type": "shell",
      "command": "API_KEY=$(vibesafe get API_KEY) npm start",
      "problemMatcher": []
    }
  ]
}
```

#### launch.json for Debugging
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "type": "node",
      "request": "launch",
      "name": "Debug with Secrets",
      "program": "${workspaceFolder}/index.js",
      "env": {
        "API_KEY": "${command:vibesafe.get.API_KEY}"
      }
    }
  ]
}
```

### JetBrains IDEs

#### Run Configuration
```xml
<!-- .idea/runConfigurations/app.xml -->
<component name="ProjectRunConfigurationManager">
  <configuration name="App with Secrets" type="NodeJSConfigurationType">
    <envs>
      <env name="API_KEY" value="$PROJECT_DIR$/scripts/get-secret.sh API_KEY" />
    </envs>
    <method v="2" />
  </configuration>
</component>
```

Where `scripts/get-secret.sh`:
```bash
#!/bin/bash
vibesafe get "$1"
```

## Security Best Practices

1. **Temporary Files**: Always clean up temporary files containing secrets
   ```bash
   # Create temp file with restricted permissions
   TMPFILE=$(mktemp)
   chmod 600 "$TMPFILE"
   vibesafe get SSL_CERT > "$TMPFILE"
   # Use the file
   # ...
   # Clean up
   shred -vfz "$TMPFILE"
   ```

2. **Process Substitution**: Prefer process substitution over temp files
   ```bash
   # Good - no file created
   some-command --key-file <(vibesafe get PRIVATE_KEY)
   
   # Avoid - creates a file
   vibesafe get PRIVATE_KEY > /tmp/key.pem
   some-command --key-file /tmp/key.pem
   ```

3. **Environment Isolation**: Clear sensitive environment variables after use
   ```bash
   # Set temporarily
   API_KEY=$(vibesafe get API_KEY) ./deploy.sh
   
   # Or unset after use
   export API_KEY=$(vibesafe get API_KEY)
   ./deploy.sh
   unset API_KEY
   ```

4. **Audit Trail**: Log secret access (without values)
   ```bash
   echo "[$(date)] Accessed secret: API_KEY for deployment" >> ~/.vibesafe/audit.log
   ```

## Troubleshooting Common Issues

### "Command not found: vibesafe"
```bash
# Add to PATH or use full path
export PATH="$PATH:$HOME/.local/bin"
# Or use: python -m vibesafe.vibesafe
```

### Authentication Timeout
```bash
# Retry with longer timeout
for i in {1..3}; do
  if API_KEY=$(vibesafe get API_KEY); then
    break
  fi
  echo "Retry $i: Waiting for authentication..."
  sleep 2
done
```

### Scripting with Error Handling
```bash
#!/bin/bash
set -e  # Exit on error

# Function to get secret with retry
get_secret() {
  local name=$1
  local value
  
  if ! value=$(vibesafe get "$name" 2>/dev/null); then
    echo "Error: Failed to get secret '$name'" >&2
    echo "Please ensure:" >&2
    echo "  1. VibeSafe is initialized (vibesafe init)" >&2
    echo "  2. Secret exists (vibesafe list)" >&2
    echo "  3. You authenticate if passkey is enabled" >&2
    exit 1
  fi
  
  echo "$value"
}

# Use in script
API_KEY=$(get_secret API_KEY)
DB_URL=$(get_secret DATABASE_URL)
```