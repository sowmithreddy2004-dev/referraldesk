import os
import shutil

BUCKET = os.environ.get("UPLOAD_BUCKET")
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads")


def save_upload(object_name: str, fileobj, content_type=None) -> str:
    """Save an upload and return the storage path to record in the DB."""
    if BUCKET:
        from google.cloud import storage  # credentials come from the VM service account
        blob = storage.Client().bucket(BUCKET).blob(object_name)
        blob.upload_from_file(fileobj, content_type=content_type)
        return f"gs://{BUCKET}/{object_name}"
    dest = os.path.join(UPLOAD_DIR, object_name)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "wb") as out:
        shutil.copyfileobj(fileobj, out)
    return dest
