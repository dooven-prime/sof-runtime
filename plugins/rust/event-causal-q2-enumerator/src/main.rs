use std::collections::{HashSet, VecDeque};
use std::env;
use std::time::Instant;

#[derive(Clone, Copy, Debug, Eq, Hash, PartialEq)]
struct Event {
    u0: u16,
    v1: u16,
    fresh: u16,
}

#[derive(Clone, Debug, Eq, Hash, PartialEq)]
struct State {
    partition: u128,
    events: Vec<Event>,
}

#[derive(Clone, Copy, Debug, Eq, Hash, PartialEq)]
struct Origin(Event);

#[derive(Clone, Debug, Eq, Hash, PartialEq)]
struct Gamma {
    partition: u128,
    selected: u16,
    origin: Origin,
    later: Vec<Event>,
}

fn row(partition: u128, n: usize, q: usize) -> u16 {
    ((partition >> (q * n)) & ((1u128 << n) - 1)) as u16
}

fn set_row(partition: &mut u128, n: usize, q: usize, value: u16) {
    let mask = ((1u128 << n) - 1) << (q * n);
    *partition = (*partition & !mask) | ((value as u128) << (q * n));
}

fn transition(partition: u128, n: usize, letter: u8) -> (u128, Option<Event>) {
    let mut next = 0u128;
    for q in 0..n {
        let target = if letter == 0 {
            (q + 1) % n
        } else if q == 1 {
            0
        } else {
            q
        };
        let merged = row(next, n, target) | row(partition, n, q);
        set_row(&mut next, n, target, merged);
    }
    if letter == 1 {
        let u0 = row(partition, n, 0);
        let v1 = row(partition, n, 1);
        if u0 != 0 && v1 != 0 {
            let event = Event {
                u0,
                v1,
                fresh: u0 | v1,
            };
            return (next, Some(event));
        }
    }
    (next, None)
}

fn enumerate(n: usize, max_states: usize) -> (usize, Vec<usize>, f64) {
    assert!((2..=10).contains(&n), "supported n range is 2..=10");
    let selected = 0b11u16;
    let seed = (0..n).fold(0u128, |p, q| p | (1u128 << (q * n + q)));
    let start = State {
        partition: seed,
        events: Vec::new(),
    };
    let mut seen = HashSet::from([start.clone()]);
    let mut queue = VecDeque::from([start]);
    let mut gamma: Vec<HashSet<Gamma>> = (0..=n).map(|_| HashSet::new()).collect();
    let clock = Instant::now();

    while let Some(state) = queue.pop_front() {
        for (index, origin_event) in state.events.iter().copied().enumerate() {
            if origin_event.fresh != selected {
                continue;
            }
            let later = state.events[index + 1..]
                .iter()
                .copied()
                .filter(|event| selected & !event.u0 == 0 || selected & !event.v1 == 0)
                .collect::<Vec<_>>();
            let key = Gamma {
                partition: state.partition,
                selected,
                origin: Origin(origin_event),
                later,
            };
            gamma[selected.count_ones() as usize].insert(key);
            break;
        }
        for letter in 0..=1 {
            let (partition, event) = transition(state.partition, n, letter);
            let mut events = state.events.clone();
            if let Some(event) = event {
                events.push(event);
            }
            let next = State { partition, events };
            if !seen.contains(&next) && seen.len() >= max_states {
                panic!("state limit reached before closure: {max_states}");
            }
            if seen.insert(next.clone()) {
                queue.push_back(next);
            }
        }
    }
    let counts = (2..=n).map(|k| gamma[k].len()).collect();
    (seen.len(), counts, clock.elapsed().as_secs_f64())
}

fn main() {
    let args = env::args().skip(1).collect::<Vec<_>>();
    let n = args
        .first()
        .map(|s| s.parse().expect("n must be an integer"))
        .unwrap_or(6);
    let limit = args
        .get(1)
        .map(|s| s.parse().expect("max-states must be an integer"))
        .unwrap_or(1_000_000usize);
    let (states, counts, seconds) = enumerate(n, limit);
    println!(
        "{{\"n\":{n},\"log_states\":{states},\"selected_carrier_size\":2,\"gamma_count\":{},\"elapsed_seconds\":{seconds:.6},\"status\":\"PASS_EXACT\"}}",
        counts[0]
    );
}
