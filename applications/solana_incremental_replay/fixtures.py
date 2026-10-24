"""V1 envelope over the unchanged v0 synthetic projection controls."""
from applications.solana_offchain_slice.common import canonical, parse, sha
from applications.solana_offchain_slice.fixtures import synthetic as v0_synthetic
from .capture import SCHEMA


def synthetic(directory):
    path = v0_synthetic(directory)
    plan = canonical({"schema": "sof-runtime.solana-incremental-fixture.v1", "range": [100, 102]})
    (path.parent / "plan.json").write_bytes(plan)
    m = parse(path.read_bytes())
    m.update(schema=SCHEMA, plan_sha256=sha(plan))
    path.write_bytes(canonical(m))
    return path
