import os
from functools import lru_cache
from urllib.parse import quote_plus


@lru_cache
def get_secret(name: str) -> str:
    # Uses the VM's service account via the metadata server. No key file.
    from google.cloud import secretmanager
    client = secretmanager.SecretManagerServiceClient()
    path = f"projects/{os.environ['GCP_PROJECT']}/secrets/{name}/versions/latest"
    return client.access_secret_version(name=path).payload.data.decode()


def database_url() -> str:
    if os.getenv("DATABASE_URL"):  # local development only
        return os.environ["DATABASE_URL"]
    pw = quote_plus(get_secret("referraldesk-db-password"))
    return f"postgresql+psycopg2://referraldesk:{pw}@{os.environ['DB_HOST']}:5432/referraldesk"
