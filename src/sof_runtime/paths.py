import os
from pathlib import Path
import sys


PACKAGE_SOURCE_ROOT = Path(__file__).resolve().parents[2]
SOURCE_CHECKOUT = (
    PACKAGE_SOURCE_ROOT
    if (PACKAGE_SOURCE_ROOT / "contracts" / "upstream.lock.json").is_file()
    else None
)
PROJECT_ROOT = Path(
    os.environ.get(
        "SOF_RUNTIME_WORKSPACE",
        str(SOURCE_CHECKOUT or Path.cwd()),
    )
).resolve()
CONTRACTS_ROOT = (
    SOURCE_CHECKOUT / "contracts"
    if SOURCE_CHECKOUT is not None
    else Path(sys.prefix).resolve() / "sof_runtime_contracts"
)
COMPILER_CONTRACT_ROOT = CONTRACTS_ROOT / "compiler" / "v1.0"
RUNTIME_CONTRACT_ROOT = CONTRACTS_ROOT / "runtime" / "v1.0"
REPORTING_CONTRACT_ROOT = CONTRACTS_ROOT / "reporting" / "v2.0"
COMPARISON_CONTRACT_ROOT = CONTRACTS_ROOT / "comparison" / "v2.0"
ACTION_CONTRACT_ROOT = CONTRACTS_ROOT / "action" / "candidate-v2.0"
RANK_COLLAPSE_CONTRACT_ROOT = (
    CONTRACTS_ROOT / "extensions" / "rank-collapse" / "v1.0"
)
AUTOMATA_CONTRACT_ROOT = CONTRACTS_ROOT / "sources" / "automata" / "v1.0"
MARKOV_CONTRACT_ROOT = CONTRACTS_ROOT / "sources" / "markov" / "v1.0"
POSITIVE_WORD_CONTRACT_ROOT = (
    CONTRACTS_ROOT / "extensions" / "positive-word-support" / "v1.0"
)
