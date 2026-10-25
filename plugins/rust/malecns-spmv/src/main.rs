use num_bigint::BigInt;
use num_rational::BigRational;
use num_traits::{One, Zero};
use rayon::prelude::*;
use serde::Deserialize;
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::fs;
use std::io::{Read, Write};
use std::path::Path;
use std::time::Instant;

type Result<T> = std::result::Result<T, String>;

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Request {
    schema: String,
    packet: String,
    packet_sha256: String,
    mode: String,
    operation: String,
    threads: usize,
    iterations: usize,
    repeats: usize,
    warmups: usize,
    vector: Vec<Value>,
}

struct Matrix {
    ptr: Vec<usize>,
    source: Vec<usize>,
    weight: Vec<u32>,
    sign: Vec<i8>,
    mass: Vec<u64>,
}

fn need(ok: bool, message: &str) -> Result<()> {
    if ok { Ok(()) } else { Err(message.into()) }
}

fn hash_file(path: &str) -> Result<String> {
    let mut file = fs::File::open(path).map_err(|e| e.to_string())?;
    let mut digest = Sha256::new();
    let mut buffer = vec![0u8; 1024 * 1024];
    loop {
        let n = file.read(&mut buffer).map_err(|e| e.to_string())?;
        if n == 0 {
            break;
        }
        digest.update(&buffer[..n]);
    }
    Ok(format!("{:x}", digest.finalize()))
}

fn parse_matrix(bytes: &[u8]) -> Result<Matrix> {
    need(
        bytes.len() >= 12 && &bytes[..8] == b"MSPMV001",
        "packet magic/truncation",
    )?;
    let size = u32::from_le_bytes(bytes[8..12].try_into().unwrap()) as usize;
    need(
        size > 0 && size <= 65536 && 12 + size <= bytes.len(),
        "header length",
    )?;
    let header: Value = serde_json::from_slice(&bytes[12..12 + size]).map_err(|e| e.to_string())?;
    need(
        header["schema"] == "sof-runtime.malecns-spmv.packet.v0",
        "packet schema",
    )?;
    let n = header["n"].as_u64().ok_or("n must be an integer")? as usize;
    let m = header["nnz"].as_u64().ok_or("nnz must be an integer")? as usize;
    need(
        (1..=1_000_000).contains(&n) && m <= 100_000_000,
        "dimension limit",
    )?;
    let expected = 12 + size + (n + 1) * 8 + m * 8 + n + n * 8;
    need(expected == bytes.len(), "packet truncated or trailing data")?;
    let mut at = 12 + size;
    let mut u64s = |count: usize| -> Vec<u64> {
        let end = at + count * 8;
        let result = bytes[at..end]
            .chunks_exact(8)
            .map(|v| u64::from_le_bytes(v.try_into().unwrap()))
            .collect();
        at = end;
        result
    };
    let ptr64 = u64s(n + 1);
    need(
        ptr64[0] == 0 && ptr64[n] == m as u64 && ptr64.windows(2).all(|w| w[0] <= w[1]),
        "row pointers",
    )?;
    let ptr: Vec<usize> = ptr64.into_iter().map(|v| v as usize).collect();
    let source: Vec<usize> = bytes[at..at + m * 4]
        .chunks_exact(4)
        .map(|v| u32::from_le_bytes(v.try_into().unwrap()) as usize)
        .collect();
    at += m * 4;
    let weight: Vec<u32> = bytes[at..at + m * 4]
        .chunks_exact(4)
        .map(|v| u32::from_le_bytes(v.try_into().unwrap()))
        .collect();
    at += m * 4;
    let sign: Vec<i8> = bytes[at..at + n].iter().map(|v| *v as i8).collect();
    at += n;
    let mass: Vec<u64> = bytes[at..]
        .chunks_exact(8)
        .map(|v| u64::from_le_bytes(v.try_into().unwrap()))
        .collect();
    need(
        sign.iter().all(|s| (-1..=1).contains(s)),
        "invalid source sign",
    )?;
    let mut sums = vec![0u64; n];
    for row in 0..n {
        let mut previous = None;
        for k in ptr[row]..ptr[row + 1] {
            let s = source[k];
            need(
                s < n && previous.is_none_or(|p| p < s),
                "invalid/duplicate/unsorted source index",
            )?;
            need(
                weight[k] > 0 && sign[s] != 0,
                "zero weight or unknown-sign edge",
            )?;
            sums[s] = sums[s]
                .checked_add(weight[k] as u64)
                .ok_or("mass overflow")?;
            previous = Some(s);
        }
    }
    need(sums == mass, "outgoing mass mismatch")?;
    Ok(Matrix {
        ptr,
        source,
        weight,
        sign,
        mass,
    })
}

fn numeric_step(
    matrix: &Matrix,
    coefficient: &[f64],
    x: &[f64],
    update: bool,
    parallel: bool,
) -> Result<Vec<f64>> {
    let row = |j: usize| -> Result<f64> {
        let mut total = 0.0;
        for k in matrix.ptr[j]..matrix.ptr[j + 1] {
            total += coefficient[k] * x[matrix.source[k]];
        }
        need(total.is_finite(), "non-finite numerical drive")?;
        Ok(if update {
            0.8 * x[j] + 0.2 * total.clamp(0.0, 1.0)
        } else {
            total
        })
    };
    let result: Vec<f64> = if parallel {
        (0..x.len())
            .into_par_iter()
            .map(row)
            .collect::<Result<_>>()?
    } else {
        (0..x.len()).map(row).collect::<Result<_>>()?
    };
    need(
        result.iter().all(|v| v.is_finite()),
        "non-finite numerical output",
    )?;
    Ok(result)
}

fn bounded(value: &BigRational) -> Result<()> {
    need(
        value.numer().bits() <= 27000 && value.denom().bits() <= 27000,
        "exact rational exceeds bit limit",
    )
}

fn exact_step(
    matrix: &Matrix,
    x: &[BigRational],
    update: bool,
    parallel: bool,
) -> Result<Vec<BigRational>> {
    let row = |j: usize| -> Result<BigRational> {
        let mut total = BigRational::zero();
        for k in matrix.ptr[j]..matrix.ptr[j + 1] {
            let s = matrix.source[k];
            if !x[s].is_zero() {
                let coefficient = BigRational::new(
                    BigInt::from(matrix.sign[s] as i64 * matrix.weight[k] as i64),
                    BigInt::from(matrix.mass[s]),
                );
                total += coefficient * &x[s];
                bounded(&total)?;
            }
        }
        if update {
            let clipped = total.max(BigRational::zero()).min(BigRational::one());
            total = (&x[j] * BigInt::from(4) + clipped) / BigInt::from(5);
            bounded(&total)?;
        }
        Ok(total)
    };
    if parallel {
        (0..x.len()).into_par_iter().map(row).collect()
    } else {
        (0..x.len()).map(row).collect()
    }
}

fn run(request: Request) -> Result<Value> {
    let start = Instant::now();
    need(
        request.schema == "sof-runtime.malecns-spmv.request.v0",
        "request schema",
    )?;
    need(
        request.mode == "numerical" || request.mode == "exact",
        "mode",
    )?;
    need(
        request.operation == "spmv" || request.operation == "update",
        "operation",
    )?;
    need(
        (1..=16).contains(&request.threads)
            && (1..=256).contains(&request.iterations)
            && (1..=9).contains(&request.repeats)
            && request.warmups <= 2,
        "execution limit",
    )?;
    need(
        request.mode != "exact" || request.iterations <= 4,
        "exact iteration limit",
    )?;
    let metadata = fs::metadata(&request.packet).map_err(|e| e.to_string())?;
    need(metadata.len() <= 1_500_000_000, "packet size limit")?;
    let bytes = fs::read(&request.packet).map_err(|e| e.to_string())?;
    need(
        format!("{:x}", Sha256::digest(&bytes)) == request.packet_sha256,
        "packet SHA-256 mismatch",
    )?;
    let matrix = parse_matrix(&bytes)?;
    drop(bytes);
    need(
        request.vector.len() == matrix.sign.len(),
        "vector dimension",
    )?;
    let read_seconds = start.elapsed().as_secs_f64();
    let pool_start = Instant::now();
    let pool = rayon::ThreadPoolBuilder::new()
        .num_threads(request.threads)
        .build()
        .map_err(|e| e.to_string())?;
    let pool_seconds = pool_start.elapsed().as_secs_f64();
    let parallel = request.threads > 1;
    let update = request.operation == "update";
    let mut samples = Vec::new();
    let mut output = Vec::new();
    let converted = Instant::now();
    let conversion_seconds;
    let decode_seconds;
    if request.mode == "numerical" {
        let coefficient: Vec<f64> = (0..matrix.source.len())
            .map(|k| {
                let s = matrix.source[k];
                matrix.sign[s] as f64 * matrix.weight[k] as f64 / matrix.mass[s] as f64
            })
            .collect();
        conversion_seconds = converted.elapsed().as_secs_f64();
        let decoded = Instant::now();
        let x: Vec<f64> = request
            .vector
            .iter()
            .map(|v| {
                v.as_f64()
                    .filter(|v| v.is_finite())
                    .ok_or("finite numerical input required".to_string())
            })
            .collect::<Result<_>>()?;
        decode_seconds = decoded.elapsed().as_secs_f64();
        for sample in 0..request.warmups + request.repeats {
            let mut state = x.clone();
            let began = Instant::now();
            pool.install(|| -> Result<()> {
                for _ in 0..request.iterations {
                    state = numeric_step(
                        &matrix,
                        &coefficient,
                        if update { &state } else { &x },
                        update,
                        parallel,
                    )?;
                }
                Ok(())
            })?;
            if sample >= request.warmups {
                samples.push(began.elapsed().as_secs_f64());
            }
            if sample + 1 == request.warmups + request.repeats {
                output = state.into_iter().map(|v| json!(v)).collect();
            }
        }
    } else {
        conversion_seconds = 0.0;
        let decoded = Instant::now();
        let x: Vec<BigRational> = request
            .vector
            .iter()
            .map(|v| -> Result<BigRational> {
                let pair = v
                    .as_array()
                    .ok_or("exact input requires decimal-string numerator/denominator pairs")?;
                need(pair.len() == 2, "rational pair")?;
                let a = pair[0].as_str().ok_or("numerator string")?;
                let b = pair[1].as_str().ok_or("denominator string")?;
                need(a.len() <= 8192 && b.len() <= 8192, "input rational size")?;
                let numerator: BigInt = a.parse().map_err(|_| "invalid numerator")?;
                let denominator: BigInt = b.parse().map_err(|_| "invalid denominator")?;
                need(
                    denominator > BigInt::zero(),
                    "positive denominator required",
                )?;
                let value = BigRational::new(numerator, denominator);
                bounded(&value)?;
                Ok(value)
            })
            .collect::<Result<_>>()?;
        decode_seconds = decoded.elapsed().as_secs_f64();
        for sample in 0..request.warmups + request.repeats {
            let mut state = x.clone();
            let began = Instant::now();
            pool.install(|| -> Result<()> {
                for _ in 0..request.iterations {
                    state =
                        exact_step(&matrix, if update { &state } else { &x }, update, parallel)?;
                }
                Ok(())
            })?;
            if sample >= request.warmups {
                samples.push(began.elapsed().as_secs_f64());
            }
            if sample + 1 == request.warmups + request.repeats {
                output = state
                    .into_iter()
                    .map(|v| json!([v.numer().to_string(), v.denom().to_string()]))
                    .collect();
            }
        }
    }
    let post = Instant::now();
    need(
        hash_file(&request.packet)? == request.packet_sha256,
        "packet changed during consumption",
    )?;
    Ok(
        json!({"status":"COMPLETED_LOCAL", "mode":request.mode,"operation":request.operation,
              "threads":request.threads,"iterations":request.iterations,"packet_sha256":request.packet_sha256,
              "output":output,"timings":{"read_hash_decode_validate_seconds":read_seconds,
              "pool_creation_seconds":pool_seconds,"coefficient_conversion_seconds":conversion_seconds,
              "vector_decode_seconds":decode_seconds,"kernel_sample_seconds":samples,
              "warmups_excluded":request.warmups,"post_packet_hash_seconds":post.elapsed().as_secs_f64(),
              "whole_internal_before_serialization_seconds":start.elapsed().as_secs_f64()}}),
    )
}

fn main() {
    let result = (|| -> Result<Value> {
        let path = std::env::args().nth(1).ok_or("expected one request path")?;
        need(
            fs::metadata(Path::new(&path))
                .map_err(|e| e.to_string())?
                .len()
                <= 32 * 1024 * 1024,
            "request size limit",
        )?;
        let bytes = fs::read(path).map_err(|e| e.to_string())?;
        let request: Request = serde_json::from_slice(&bytes).map_err(|e| e.to_string())?;
        run(request)
    })();
    match result {
        Ok(value) => {
            if let Err(error) = serde_json::to_writer(std::io::stdout().lock(), &value) {
                eprintln!("output failure: {error}");
                std::process::exit(2);
            }
            let _ = std::io::stdout().write_all(b"\n");
        }
        Err(error) => {
            println!("{}", json!({"status":"UNRESOLVED","detail":error}));
            std::process::exit(2);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn exact_clip_sees_below_binary64_resolution() {
        let matrix = Matrix {
            ptr: vec![0, 1, 1],
            source: vec![0],
            weight: vec![1],
            sign: vec![1, 0],
            mass: vec![1, 0],
        };
        let epsilon = BigRational::new(BigInt::one(), BigInt::one() << 100);
        let x = vec![BigRational::one() + &epsilon, BigRational::zero()];
        let result = exact_step(&matrix, &x, true, false).unwrap();
        assert_eq!(
            result[0],
            BigRational::one() + epsilon * BigRational::new(4.into(), 5.into())
        );
    }
}
