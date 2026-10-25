# MaleCNS SpMV v0

Fresh-process application kernel; it does not implement a general plugin ABI.
The [application contract](../../../applications/malecns_sparse_kernel/CONTRACT.md)
owns arithmetic, target-row packet and cost semantics.

```text
malecns-spmv REQUEST.json
```

The JSON request binds a packet SHA-256, arithmetic mode, operation, complete
vector, explicit threads, iterations, warmups and repeats. It emits complete
output coordinates and nested timing fields. Error/resource stops exit 2 with
UNRESOLVED, not an approximate exact answer. The Python parent supplies timeout
and sampled RSS limits; the binary is not a sandbox.

Numerical mode computes each target row in ascending source order. Rayon only
distributes whole rows. Exact mode uses reduced arbitrary-precision rationals,
including exact comparisons to 0 and 1. No f64 path implements exact mode.
Coefficients are prepared once for numerical samples. Exact coefficients and
rational arithmetic are included in exact kernel cost.

Limits: request 32 MiB; packet 1.5 GB; at most 1,000,000 nodes/100,000,000 edges;
threads 1--16, samples 1--9, warmups 0--2, iterations 1--256 (exact 1--4), and
rational numerator/denominator at most 27,000 bits. Reject invalid mass/sign,
pointer/source ordering, checksums, truncation and trailing data. Verify the
whole packet again after consumption; no immutable-storage claim is implied.
