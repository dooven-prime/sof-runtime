"""Clearly synthetic protocol controls, not RPC evidence."""
from copy import deepcopy
from pathlib import Path

from .common import CONFIG,PROJECTION,SCHEMA,canonical,parse,sha

ALPHABET="123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def b58(number,size=32):
    raw=number.to_bytes(size,"big");v=int.from_bytes(raw,"big");text=""
    while v: v,r=divmod(v,58);text=ALPHABET[r]+text
    return "1"*(len(raw)-len(raw.lstrip(b"\0")))+text


def synthetic(directory):
    root=Path(directory);root.mkdir(parents=True,exist_ok=False);entries={};counter=0
    def save(role,method,params,result):
        nonlocal counter
        counter+=1;req=canonical({"jsonrpc":"2.0","id":counter,"method":method,"params":params})
        reply=canonical({"jsonrpc":"2.0","id":counter,"result":result})
        a=f"{role}.request.json";b=f"{role}.response.json";(root/a).write_bytes(req);(root/b).write_bytes(reply)
        entries[role]={"id":counter,"method":method,"params":params,"request":a,"response":b,
                       "request_sha256":sha(req),"response_sha256":sha(reply)}
    version={"solana-core":"synthetic-control","feature-set":0};genesis=b58(1)
    save("version","getVersion",[],version);save("genesis","getGenesisHash",[],genesis)
    save("genesis_after","getGenesisHash",[],genesis)
    for role in ("root_before","root_after"):save(role,"getSlot",[{"commitment":"finalized"}],200)
    for role in ("index_before","index_after"):save(role,"getBlocks",[100,102,{"commitment":"finalized"}],[100,102])
    save("anchor","getBlock",[99,{**CONFIG,"transactionDetails":"none"}],{"blockhash":b58(99)})
    transaction={"version":"legacy","transaction":{"signatures":[b58(7,64)],"message":{
        "header":{"numRequiredSignatures":1,"numReadonlySignedAccounts":0,"numReadonlyUnsignedAccounts":1},
        "accountKeys":[b58(1),b58(2)],"recentBlockhash":b58(98),
        "instructions":[{"programIdIndex":1,"accounts":[0],"data":"111"}]}},
        "meta":{"fee":5000,"err":None,"loadedAddresses":{"writable":[],"readonly":[]}}}
    v0=deepcopy(transaction);v0["version"]=0;v0["transaction"]["signatures"]=[b58(8,64)]
    v0["transaction"]["message"]["addressTableLookups"]=[{"accountKey":b58(20),"writableIndexes":[2],"readonlyIndexes":[3]}]
    v0["meta"]["loadedAddresses"]={"writable":[b58(3)],"readonly":[b58(4)]}
    v0["transaction"]["message"]["instructions"][0]={"programIdIndex":3,"accounts":[0,2],"data":""}
    v0["meta"]["err"]={"InstructionError":[0,{"Custom":42}]}
    blocks=[]
    for slot,parent,txs in ((100,99,[transaction,v0]),(102,100,[transaction,transaction])):
        block={"blockhash":b58(slot),"previousBlockhash":b58(parent),"parentSlot":parent,
               "blockHeight":50 if slot==100 else 51,"blockTime":None,"transactions":txs}
        role=f"block-{slot}";save(role,"getBlock",[slot,CONFIG],block)
        blocks.append({"slot":slot,"role":role,"blockhash":b58(slot)})
    manifest={"schema":SCHEMA,"projection":PROJECTION,"capture_kind":"synthetic_control","source":"synthetic://local",
              "commitment":"finalized","config":CONFIG,"genesis":genesis,"server_version":version,
              "start_slot":100,"end_slot":102,"listed_blocks":blocks,"anchor":{"slot":99,"blockhash":b58(99)},
              "rpc":entries,"finality_independently_verified":False}
    (root/"manifest.json").write_bytes(canonical(manifest));return root/"manifest.json"


def change_response(manifest_path,role,transform):
    path=Path(manifest_path);m=parse(path.read_bytes());entry=m["rpc"][role];target=path.parent/entry["response"]
    value=parse(target.read_bytes());transform(value);raw=canonical(value);target.write_bytes(raw)
    entry["response_sha256"]=sha(raw);path.write_bytes(canonical(m))
