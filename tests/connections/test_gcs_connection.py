"""Connection test: Google Cloud Storage bucket access."""
import os

import pytest

pytestmark = pytest.mark.connection

STORAGE_BACKEND = os.environ.get("STORAGE_BACKEND", "local")
GCS_BUCKET = os.environ.get("GCS_BUCKET", "")


@pytest.fixture(autouse=True)
def skip_if_not_gcs():
    if STORAGE_BACKEND != "gcs":
        pytest.skip("STORAGE_BACKEND is not 'gcs'")
    if not GCS_BUCKET:
        pytest.skip("GCS_BUCKET not set")


def test_gcs_bucket_is_accessible():
    """Reads bucket metadata to verify the bucket exists and credentials work."""
    try:
        from google.cloud import storage
        client = storage.Client()
        bucket = client.get_bucket(GCS_BUCKET)
        assert bucket is not None
        print(f"\n  Bucket: gs://{GCS_BUCKET}")
        print(f"  Location: {bucket.location}")
        print("  Status: GCS ACCESSIBLE ✓")
    except Exception as e:
        pytest.fail(
            f"GCS bucket '{GCS_BUCKET}' is not accessible: {e}\n"
            "Check: bucket exists, ADC credentials have Storage Object Admin role"
        )


def test_gcs_write_and_read_roundtrip():
    """Writes a small test object and reads it back to verify read/write access."""
    try:
        from google.cloud import storage
        import uuid

        client = storage.Client()
        bucket = client.bucket(GCS_BUCKET)
        blob_name = f"test/connection_check_{uuid.uuid4().hex[:8]}.txt"
        blob = bucket.blob(blob_name)

        test_content = "ad-synth-ai connection test"
        blob.upload_from_string(test_content, content_type="text/plain")

        downloaded = blob.download_as_text()
        assert downloaded == test_content

        blob.delete()
        print(f"\n  Write/read/delete roundtrip on gs://{GCS_BUCKET} ✓")
        print("  Status: GCS READ/WRITE ✓")
    except Exception as e:
        pytest.fail(f"GCS read/write test failed: {e}")
