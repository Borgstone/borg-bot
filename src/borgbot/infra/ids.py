import uuid
def run_id() -> str:
    # short, log-friendly run id
    return uuid.uuid4().hex[:8]
