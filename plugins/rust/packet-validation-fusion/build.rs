use quote::{ToTokens, quote};
use sha2::{Digest, Sha256};
use std::{env, fs, path::PathBuf};
use syn::{Expr, Item, ItemFn, Stmt, parse_quote, visit_mut::VisitMut};

const SOURCE_SHA: &str = "dab41011eea745e276a4b54794c20ab29ad1279bb94bafdf60204619639cb422";

fn tokens(value: &impl ToTokens) -> String {
    value.to_token_stream().to_string()
}

struct TrackOpen(usize);
impl VisitMut for TrackOpen {
    fn visit_expr_mut(&mut self, node: &mut Expr) {
        if let Expr::Call(call) = node {
            if tokens(&call.func) == "File :: open" {
                call.func = Box::new(parse_quote!(tracked_open));
                self.0 += 1;
            }
        }
        syn::visit_mut::visit_expr_mut(self, node);
    }
}

fn main() {
    let source = PathBuf::from(env::var_os("CARGO_MANIFEST_DIR").unwrap())
        .join("../prepared-input-cache/src/main.rs");
    println!("cargo:rerun-if-changed={}", source.display());
    println!("cargo:rerun-if-changed=build.rs");
    let raw = fs::read(&source).expect("read pinned reference");
    assert_eq!(
        format!("{:x}", Sha256::digest(&raw)),
        SOURCE_SHA,
        "reference changed"
    );
    let mut file = syn::parse_file(std::str::from_utf8(&raw).unwrap()).unwrap();
    let validator = file
        .items
        .iter()
        .filter_map(|item| match item {
            Item::Fn(function) if function.sig.ident == "validate_packet" => Some(function.clone()),
            _ => None,
        })
        .collect::<Vec<_>>();
    assert_eq!(validator.len(), 1);
    let original = &validator[0];
    let expected: ItemFn = parse_quote!(
        fn validate_packet(path: &Path, identity: &Value) -> Outcome<Packet> {}
    );
    assert_eq!(tokens(&original.sig), tokens(&expected.sig));
    let prefix: Vec<Stmt> = vec![
        parse_quote!(regular(path)?;),
        parse_quote!(let (size, sha256) = hash_file(path)?;),
        parse_quote!(let mut reader = BufReader::new(File::open(path).map_err(|e| e.to_string())?);),
    ];
    for (actual, expected) in original.block.stmts.iter().zip(&prefix) {
        assert_eq!(tokens(actual), tokens(expected), "validator prefix changed");
    }
    let expected_end = Stmt::Expr(
        parse_quote!(Ok(Packet {
            name: "packet.bin".into(),
            size,
            sha256,
            header,
            record_count: count,
            edge_count: edges,
        })),
        None,
    );
    assert_eq!(
        tokens(original.block.stmts.last().unwrap()),
        tokens(&expected_end)
    );
    let mut parser: ItemFn = parse_quote!(
        fn parse_packet(mut reader: &mut impl Read, identity: &Value) -> Outcome<ParsedPacket> {}
    );
    parser.block.stmts = original.block.stmts[3..original.block.stmts.len() - 1].to_vec();
    parser.block.stmts.push(Stmt::Expr(
        parse_quote!(Ok(ParsedPacket {
            header,
            record_count: count,
            edge_count: edges,
        })),
        None,
    ));

    let mut tracked = TrackOpen(0);
    let mut renamed = 0;
    for item in &mut file.items {
        if let Item::Fn(function) = item {
            if function.sig.ident == "validate_packet" {
                function.sig.ident =
                    syn::Ident::new("validate_packet_reference", function.sig.ident.span());
                renamed += 1;
                tracked.visit_block_mut(&mut function.block);
            } else if function.sig.ident == "hash_file" {
                tracked.visit_block_mut(&mut function.block);
            }
        }
    }
    assert_eq!(renamed, 1);
    assert_eq!(tracked.0, 2, "unexpected read-open sites");
    file.items.push(Item::Fn(parser));
    let output = PathBuf::from(env::var_os("OUT_DIR").unwrap()).join("reference.rs");
    fs::write(output, quote!(#file).to_string()).unwrap();
}
