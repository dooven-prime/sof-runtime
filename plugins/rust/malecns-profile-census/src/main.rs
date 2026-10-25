use serde::Deserialize;
use serde_json::json;
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, HashMap, HashSet};
use std::env;
use std::fs::File;
use std::io::{self, BufReader, Read};
use std::process::ExitCode;
use std::time::Instant;

const MAGIC: &[u8; 8] = b"RIMEPC01";
const INPUT_SCHEMA: &str = "rime.malecns.profile-census-input.v1";
const MAX_I64: u64 = i64::MAX as u64;

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Header {
    schema: String,
    source_field: String,
    source_identity: String,
    sign_semantics: String,
    sector_labels: Vec<String>,
    record_count: u64,
    source_artifacts: Vec<SourceArtifact>,
}

#[derive(Deserialize, serde::Serialize)]
#[serde(deny_unknown_fields)]
struct SourceArtifact {
    role: String,
    name: String,
    size: u64,
    sha256: String,
}

fn read_exact<const N: usize>(reader: &mut impl Read) -> io::Result<[u8; N]> {
    let mut bytes = [0u8; N];
    reader.read_exact(&mut bytes)?;
    Ok(bytes)
}

fn gcd(mut left: u64, mut right: u64) -> u64 {
    while right != 0 {
        (left, right) = (right, left % right);
    }
    left
}

fn coordinate_ratio(signature: &[u64], coordinate: usize) -> (u64, u64) {
    let denominator = signature[0];
    let numerator = signature[coordinate + 1];
    let divisor = gcd(denominator, numerator);
    (numerator / divisor, denominator / divisor)
}

fn minimal_separators(signatures: &[Vec<u64>], labels: &[String]) -> Option<Vec<Vec<String>>> {
    let dimension = labels.len();
    if dimension > 8 {
        return None;
    }
    let limit = 1u64 << dimension;
    for width in 0..=dimension {
        let mut answers = Vec::new();
        for mask in 0..limit {
            if mask.count_ones() as usize != width {
                continue;
            }
            let coordinates = (0..dimension)
                .filter(|coordinate| mask & (1 << coordinate) != 0)
                .collect::<Vec<_>>();
            let mut projections = HashSet::new();
            let mut unique = true;
            for signature in signatures {
                let projection = coordinates
                    .iter()
                    .map(|coordinate| coordinate_ratio(signature, *coordinate))
                    .collect::<Vec<_>>();
                if !projections.insert(projection) {
                    unique = false;
                    break;
                }
            }
            if unique {
                answers.push(coordinates);
            }
        }
        if !answers.is_empty() {
            // Match Python combinations in basis-index order, not label order.
            answers.sort();
            return Some(
                answers
                    .into_iter()
                    .map(|coordinates| {
                        coordinates.into_iter().map(|index| labels[index].clone()).collect()
                    })
                    .collect(),
            );
        }
    }
    Some(Vec::new())
}

fn minimal_global_separators(
    classes: &[BTreeMap<Vec<u64>, u64>],
    labels: &[String],
) -> Option<Vec<Vec<String>>> {
    let dimension = labels.len();
    if dimension > 8 {
        return None;
    }
    let limit = 1u64 << dimension;
    for width in 0..=dimension {
        let mut answers = Vec::new();
        for mask in 0..limit {
            if mask.count_ones() as usize != width {
                continue;
            }
            let coordinates = (0..dimension)
                .filter(|coordinate| mask & (1 << coordinate) != 0)
                .collect::<Vec<_>>();
            let separates_every_fiber = classes.iter().all(|sector_classes| {
                let mut projections = HashSet::new();
                sector_classes.keys().all(|signature| {
                    let projection = coordinates
                        .iter()
                        .map(|coordinate| coordinate_ratio(signature, *coordinate))
                        .collect::<Vec<_>>();
                    projections.insert(projection)
                })
            });
            if separates_every_fiber {
                answers.push(coordinates);
            }
        }
        if !answers.is_empty() {
            answers.sort();
            return Some(
                answers
                    .into_iter()
                    .map(|coordinates| {
                        coordinates.into_iter().map(|index| labels[index].clone()).collect()
                    })
                    .collect(),
            );
        }
    }
    Some(Vec::new())
}

fn run(input: &str, report_metrics: bool) -> Result<(), Box<dyn std::error::Error>> {
    let started = Instant::now();
    let file = File::open(input)?;
    let mut reader = BufReader::new(file);
    let magic = read_exact::<8>(&mut reader)?;
    if &magic != MAGIC {
        return Err("invalid profile-census packet magic".into());
    }
    let header_length = u32::from_le_bytes(read_exact::<4>(&mut reader)?) as usize;
    if header_length == 0 || header_length > 1_000_000 {
        return Err("invalid profile-census header length".into());
    }
    let header_bytes = (0..header_length)
        .map(|_| read_exact::<1>(&mut reader).map(|byte| byte[0]))
        .collect::<io::Result<Vec<_>>>()?;
    let header: Header = serde_json::from_slice(&header_bytes)?;
    let header_value: serde_json::Value = serde_json::from_slice(&header_bytes)?;
    if serde_json::to_vec(&header_value)? != header_bytes {
        return Err("profile-census header is not canonically encoded".into());
    }
    if header.schema != INPUT_SCHEMA
        || header.source_field.is_empty()
        || header.source_identity.is_empty()
        || header.sign_semantics.is_empty()
        || header.sector_labels.is_empty()
        || header.sector_labels.iter().any(String::is_empty)
        || header.sector_labels.iter().collect::<HashSet<_>>().len() != header.sector_labels.len()
        || header.record_count > MAX_I64
        || header.source_artifacts.iter().any(|artifact| {
            artifact.role.is_empty()
                || artifact.name.is_empty()
                || artifact.size > MAX_I64
                || artifact.sha256.len() != 64
                || !artifact.sha256.bytes().all(|byte| byte.is_ascii_hexdigit())
        })
    {
        return Err("invalid profile-census header fields".into());
    }

    let sector_count = header.sector_labels.len();
    if sector_count > u16::MAX as usize {
        return Err("sector basis exceeds the input format".into());
    }
    let mut classes = (0..sector_count)
        .map(|_| BTreeMap::<Vec<u64>, u64>::new())
        .collect::<Vec<_>>();
    let mut previous_source = None;
    let header_seconds = started.elapsed().as_secs_f64();
    let aggregate_started = Instant::now();
    let mut total_edges = 0u64;

    for _ in 0..header.record_count {
        let source = u64::from_le_bytes(read_exact::<8>(&mut reader)?);
        let source_sector = u16::from_le_bytes(read_exact::<2>(&mut reader)?) as usize;
        let sign = i8::from_le_bytes(read_exact::<1>(&mut reader)?);
        let edge_count = u32::from_le_bytes(read_exact::<4>(&mut reader)?);
        if source > MAX_I64
            || previous_source.is_some_and(|previous| source <= previous)
            || source_sector >= sector_count
            || !matches!(sign, -1 | 1)
            || edge_count == 0
        {
            return Err("invalid or unordered profile-census source record".into());
        }
        previous_source = Some(source);
        total_edges = total_edges.checked_add(u64::from(edge_count)).ok_or("edge count overflow")?;

        let mut mass = 0u64;
        let mut positive = vec![0u64; sector_count];
        for _ in 0..edge_count {
            let target_sector = u16::from_le_bytes(read_exact::<2>(&mut reader)?) as usize;
            let weight = u64::from_le_bytes(read_exact::<8>(&mut reader)?);
            if target_sector >= sector_count || weight == 0 || weight > MAX_I64 {
                return Err("invalid profile-census edge".into());
            }
            mass = mass
                .checked_add(weight)
                .filter(|value| *value <= MAX_I64)
                .ok_or("source row mass exceeds the signed 64-bit bound")?;
            if sign > 0 {
                positive[target_sector] = positive[target_sector]
                    .checked_add(weight)
                    .filter(|value| *value <= MAX_I64)
                    .ok_or("positive sector mass exceeds the signed 64-bit bound")?;
            }
        }
        let divisor = positive
            .iter()
            .fold(mass, |current, value| gcd(current, *value));
        let mut signature = Vec::with_capacity(sector_count + 1);
        signature.push(mass / divisor);
        signature.extend(positive.into_iter().map(|value| value / divisor));
        let count = classes[source_sector].entry(signature).or_insert(0);
        *count = count.checked_add(1).ok_or("profile class count overflow")?;
    }
    let mut trailing = [0u8; 1];
    if reader.read(&mut trailing)? != 0 {
        return Err("trailing bytes after profile-census records".into());
    }
    let aggregate_seconds = aggregate_started.elapsed().as_secs_f64();
    let classify_started = Instant::now();

    let mut class_rows: Vec<(usize, Vec<u64>, u64)> = Vec::new();
    let mut sectors = Vec::new();
    let mut total_classes = 0u64;
    let mut total_sources = 0u64;
    for (sector_index, sector_classes) in classes.iter().enumerate() {
        let signatures = sector_classes.keys().cloned().collect::<Vec<_>>();
        let frequencies = sector_classes.values().copied().collect::<Vec<_>>();
        for (signature, count) in sector_classes {
            class_rows.push((sector_index, signature.clone(), *count));
        }
        let class_count = signatures.len() as u64;
        let source_count = frequencies.iter().sum::<u64>();
        let largest_class = frequencies.iter().copied().max().unwrap_or(0);
        let pair_count = class_count * class_count.saturating_sub(1) / 2;
        let mut separated = Vec::with_capacity(sector_count);
        for coordinate in 0..sector_count {
            let mut same = HashMap::<(u64, u64), u64>::new();
            for signature in &signatures {
                *same
                    .entry(coordinate_ratio(signature, coordinate))
                    .or_insert(0) += 1;
            }
            let same_pairs = same
                .values()
                .map(|count| count * count.saturating_sub(1) / 2)
                .sum::<u64>();
            separated.push(pair_count - same_pairs);
        }
        total_classes += class_count;
        total_sources += source_count;
        sectors.push(json!({
            "sector_index": sector_index,
            "sector_label": header.sector_labels[sector_index],
            "eligible_sources": source_count,
            "profile_classes": class_count,
            "largest_class_sources": largest_class,
            "class_pairs": pair_count,
            "coordinate_separated_class_pairs": separated,
            "minimum_separating_coordinate_sets": minimal_separators(&signatures, &header.sector_labels),
        }));
    }
    let digest_bytes = serde_json::to_vec(&class_rows)?;
    let profile_digest = format!("{:x}", Sha256::digest(digest_bytes));
    let result = json!({
        "schema": "rime.malecns.profile-census-result.v1",
        "status": "EXACT_CENSUS",
        "source_field": header.source_field,
        "source_identity": header.source_identity,
        "sign_semantics": header.sign_semantics,
        "sector_labels": header.sector_labels,
        "eligible_sources": total_sources,
        "profile_classes": total_classes,
        "profile_classes_sha256": profile_digest,
        "minimum_global_separating_coordinate_sets":
            minimal_global_separators(&classes, &header.sector_labels),
        "sectors": sectors,
        "source_artifacts": header.source_artifacts,
        "claim_boundary": "exact integer profile census for the supplied finite input; no biological inference or paper admission",
    });
    let classify_seconds = classify_started.elapsed().as_secs_f64();
    let serialize_started = Instant::now();
    let encoded = serde_json::to_string(&result)?;
    let serialize_seconds = serialize_started.elapsed().as_secs_f64();
    println!("{encoded}");
    if report_metrics {
        eprintln!("SOF_PROFILE_METRICS {}", json!({
            "header_decode_seconds": header_seconds,
            "stream_decode_validate_aggregate_seconds": aggregate_seconds,
            "classify_report_seconds": classify_seconds,
            "serialize_seconds": serialize_seconds,
            "edge_count": total_edges,
            "record_count": header.record_count,
        }));
    }
    Ok(())
}

fn main() -> ExitCode {
    let mut args = env::args().skip(1);
    let Some(input) = args.next() else {
        eprintln!("usage: malecns-profile-census INPUT.bin [--metrics]");
        return ExitCode::from(2);
    };
    let report_metrics = match args.next().as_deref() {
        None => false,
        Some("--metrics") => true,
        Some(_) => {
            eprintln!("malecns-profile-census: unexpected argument");
            return ExitCode::from(2);
        }
    };
    if args.next().is_some() {
        eprintln!("malecns-profile-census: unexpected argument");
        return ExitCode::from(2);
    }
    match run(&input, report_metrics) {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) => {
            eprintln!("malecns-profile-census: {error}");
            ExitCode::from(2)
        }
    }
}

#[cfg(test)]
mod tests {
    use super::{minimal_global_separators, minimal_separators};

    #[test]
    fn singleton_separators_keep_nonlexicographic_basis_order() {
        let labels = vec!["Z".to_owned(), "A".to_owned()];
        let signatures = vec![vec![1, 1, 0], vec![1, 0, 1]];
        let expected = vec![vec!["Z".to_owned()], vec!["A".to_owned()]];
        assert_eq!(minimal_separators(&signatures, &labels), Some(expected.clone()));
        let classes = vec![signatures.into_iter().map(|signature| (signature, 1)).collect()];
        assert_eq!(minimal_global_separators(&classes, &labels), Some(expected));
    }

    #[test]
    fn multicoordinate_separators_use_lexicographic_indices_not_masks() {
        let labels = vec!["Z".to_owned(), "A".to_owned(), "Y".to_owned(), "B".to_owned()];
        let signatures = vec![
            vec![1, 0, 0, 0, 0],
            vec![2, 1, 1, 0, 0],
            vec![2, 0, 0, 1, 1],
            vec![4, 1, 1, 1, 1],
        ];
        let expected = vec![
            vec!["Z".to_owned(), "Y".to_owned()],
            vec!["Z".to_owned(), "B".to_owned()],
            vec!["A".to_owned(), "Y".to_owned()],
            vec!["A".to_owned(), "B".to_owned()],
        ];
        assert_eq!(minimal_separators(&signatures, &labels), Some(expected.clone()));
        let classes = vec![signatures.into_iter().map(|signature| (signature, 1)).collect()];
        assert_eq!(minimal_global_separators(&classes, &labels), Some(expected));
    }
}
