"""Separate Python projection of the declared raw-JSON capture language."""
from pathlib import Path

from .common import CONFIG,PROJECTION,SCHEMA,canonical,parse,response,sha

ALPHABET="123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def integer(value,maximum=2**64-1,minimum=0):
    if type(value) is not int or not minimum<=value<=maximum: raise ValueError("integer bounds/type")
    return value


def base58(value,size=None):
    if not isinstance(value,str) or len(value)>8192: raise ValueError("base58 string")
    number=0
    for char in value:
        if char not in ALPHABET: raise ValueError("invalid base58")
        number=number*58+ALPHABET.index(char)
    length=(number.bit_length()+7)//8+len(value)-len(value.lstrip("1"))
    if size is not None and length!=size: raise ValueError("base58 decoded length")
    return value


def keys(value):
    if not isinstance(value,list): raise ValueError("address list")
    return [base58(item,32) for item in value]


def error_json(value):
    if value is None or type(value) is bool or type(value) is str: return value
    if type(value) is int: return integer(value,2**64-1,-2**63)
    if type(value) is list: return [error_json(x) for x in value]
    if type(value) is dict: return {key:error_json(x) for key,x in value.items()}
    raise ValueError("non-integral projected error JSON")


def project_block(slot,block):
    transactions=block["transactions"]
    if not isinstance(transactions,list): raise ValueError("transaction list")
    parent=integer(block["parentSlot"])
    if parent>=slot: raise ValueError("parent order")
    height=block["blockHeight"]; timestamp=block["blockTime"]
    if height is not None: integer(height)
    if timestamp is not None: integer(timestamp,2**63-1,-2**63)
    records=[{"kind":"block","slot":slot,"blockhash":base58(block["blockhash"],32),
              "previous_blockhash":base58(block["previousBlockhash"],32),"parent_slot":parent,
              "block_height":height,"block_time":timestamp,"transaction_count":len(transactions)}]
    for index,entry in enumerate(transactions):
        version=entry["version"]
        if not (version=="legacy" or (type(version) is int and version==0)): raise ValueError("unsupported transaction version")
        transaction=entry["transaction"]; message=transaction["message"]; meta=entry["meta"]
        if not isinstance(meta,dict): raise ValueError("missing full transaction metadata")
        static=keys(message["accountKeys"]); header=message["header"]
        needed=integer(header["numRequiredSignatures"],255,1)
        readonly_signed=integer(header["numReadonlySignedAccounts"],255)
        readonly_unsigned=integer(header["numReadonlyUnsignedAccounts"],255)
        if needed>len(static) or readonly_signed>needed or readonly_unsigned>len(static)-needed: raise ValueError("message header counts")
        signatures=transaction["signatures"]
        if not isinstance(signatures,list) or len(signatures)!=needed: raise ValueError("signature count")
        signatures=[base58(sig,64) for sig in signatures]
        loaded=meta.get("loadedAddresses")
        if loaded is None:
            if version!="legacy": raise ValueError("missing v0 loaded addresses")
            loaded={"writable":[],"readonly":[]}
        writable=keys(loaded["writable"]); readonly=keys(loaded["readonly"])
        lookups=message.get("addressTableLookups",[])
        if not isinstance(lookups,list): raise ValueError("lookup list")
        if version=="legacy" and (writable or readonly or lookups): raise ValueError("legacy transaction has lookups")
        normalized=[]; nw=nr=0
        for lookup in lookups:
            w=[integer(x,255) for x in lookup["writableIndexes"]]; r=[integer(x,255) for x in lookup["readonlyIndexes"]]
            nw+=len(w); nr+=len(r)
            normalized.append({"account_key":base58(lookup["accountKey"],32),"writable_indexes":w,"readonly_indexes":r})
        if (nw,nr)!=(len(writable),len(readonly)): raise ValueError("loaded address counts")
        addresses=static+writable+readonly
        if len(addresses)>256: raise ValueError("account index width")
        instructions=[]
        for instruction in message["instructions"]:
            program=integer(instruction["programIdIndex"],255)
            accounts=[integer(x,255) for x in instruction["accounts"]]
            if program>=len(addresses) or any(i>=len(addresses) for i in accounts): raise ValueError("instruction index out of range")
            instructions.append({"program_id_index":program,"program_id":addresses[program],
                                 "account_indices":accounts,"accounts":[addresses[i] for i in accounts],"data_base58":base58(instruction["data"])})
        records.append({"kind":"transaction","slot":slot,"transaction_index":index,"version":version,
                        "signatures":signatures,"fee":integer(meta["fee"]),"error":error_json(meta["err"]),
                        "recent_blockhash":base58(message["recentBlockhash"],32),
                        "header":{"required_signatures":needed,"readonly_signed":readonly_signed,"readonly_unsigned":readonly_unsigned},
                        "static_keys":static,"loaded_writable":writable,"loaded_readonly":readonly,
                        "address_table_lookups":normalized,"instructions":instructions})
    return records


def load_capture(manifest_path):
    path=Path(manifest_path); root=path.parent.resolve()
    if path.is_symlink() or path.stat().st_size>1024**2: raise ValueError("manifest size/type")
    raw=path.read_bytes(); manifest=parse(raw)
    if manifest["schema"]!=SCHEMA or manifest["projection"]!=PROJECTION or canonical(manifest["config"])!=canonical(CONFIG) or manifest["commitment"]!="finalized":
        raise ValueError("capture contract mismatch")
    if manifest["capture_kind"] not in ("rpc_capture","synthetic_control") or manifest["finality_independently_verified"] is not False:
        raise ValueError("capture provenance boundary")
    start=integer(manifest["start_slot"]); end=integer(manifest["end_slot"])
    if not 1<=end-start+1<=16: raise ValueError("range size/order")
    values={role:response(root,entry) for role,entry in manifest["rpc"].items()}
    required={"version","genesis","genesis_after","root_before","root_after","index_before","index_after","anchor"}
    listed=manifest["listed_blocks"]
    if not listed or not isinstance(listed,list): raise ValueError("empty/invalid block list")
    slots=[integer(b["slot"]) for b in listed]
    if slots!=sorted(set(slots)) or any(not start<=s<=end for s in slots): raise ValueError("block list order/coverage")
    if set(values)!=required|{f"block-{s}" for s in slots}: raise ValueError("RPC role inventory")
    def call(role,method,params):
        item=manifest["rpc"][role]
        if item["method"]!=method or canonical(item["params"])!=canonical(params): raise ValueError("RPC role/parameters mismatch")
    for role in ("root_before","root_after"):
        call(role,"getSlot",[{"commitment":"finalized"}])
        if integer(values[role])<end: raise ValueError("root below capture range")
    for role in ("index_before","index_after"):
        call(role,"getBlocks",[start,end,{"commitment":"finalized"}])
        if canonical(values[role])!=canonical(slots): raise ValueError("source index differs from manifest")
    call("version","getVersion",[])
    if canonical(values["version"])!=canonical(manifest["server_version"]) or not isinstance(values["version"]["solana-core"],str): raise ValueError("version metadata")
    for role in ("genesis","genesis_after"):
        call(role,"getGenesisHash",[])
        if values[role]!=base58(manifest["genesis"],32): raise ValueError("cluster mismatch")
    anchor=manifest["anchor"]; anchor_slot=integer(anchor["slot"])
    call("anchor","getBlock",[anchor_slot,{**CONFIG,"transactionDetails":"none"}])
    if values["anchor"]["blockhash"]!=base58(anchor["blockhash"],32): raise ValueError("anchor data mismatch")
    previous_slot=anchor_slot; previous_hash=anchor["blockhash"]; segments=[]; known={b["slot"]:b for b in listed}
    for slot in range(start,end+1):
        if slot not in known:
            records=[{"kind":"not_listed_by_source","slot":slot}]
        else:
            entry=known[slot]
            if entry["role"]!=f"block-{slot}": raise ValueError("block role mismatch")
            call(entry["role"],"getBlock",[slot,CONFIG]); block=values[entry["role"]]
            records=project_block(slot,block)
            if block["blockhash"]!=entry["blockhash"] or block["parentSlot"]!=previous_slot or block["previousBlockhash"]!=previous_hash:
                raise ValueError("captured block chain mismatch")
            previous_slot=slot; previous_hash=block["blockhash"]
        segments.append({"slot":slot,"bytes":b"".join(canonical(record)+b"\n" for record in records),"records":len(records)})
    return manifest,sha(raw),segments


def projection(manifest_path):
    _,_,segments=load_capture(manifest_path)
    return b"".join(segment["bytes"] for segment in segments)
