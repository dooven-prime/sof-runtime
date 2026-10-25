"""Read-only, finite finalized RPC capture; failures never become skipped slots."""
from datetime import datetime,timezone
import argparse
from pathlib import Path
import urllib.parse
import urllib.request

from .common import CONFIG,SCHEMA,canonical,parse,sha


def capture(directory,endpoint="https://api.devnet.solana.com",start=None,count=3):
    url=urllib.parse.urlsplit(endpoint)
    if url.scheme!="https" or url.username or url.password or url.query or url.fragment:
        raise ValueError("use a public HTTPS endpoint without embedded credentials")
    if type(count) is not int or not 1<=count<=16: raise ValueError("capture count 1--16")
    root=Path(directory); root.mkdir(parents=True,exist_ok=False)
    entries={}; calls=0
    def rpc(role,method,params):
        nonlocal calls
        calls+=1; request={"jsonrpc":"2.0","id":calls,"method":method,"params":params}
        encoded=canonical(request)
        with urllib.request.urlopen(urllib.request.Request(endpoint,encoded,{"Content-Type":"application/json","Accept-Encoding":"identity"}),timeout=30) as reply:
            if reply.status!=200: raise ValueError("HTTP failure")
            raw=reply.read(32*1024**2+1)
        if len(raw)>32*1024**2: raise ValueError("RPC byte limit")
        request_name=f"{calls:03d}-{role}.request.json"; response_name=f"{calls:03d}-{role}.response.json"
        (root/request_name).write_bytes(encoded); (root/response_name).write_bytes(raw)
        result=parse(raw)
        if result.get("jsonrpc")!="2.0" or result.get("id")!=calls or "error" in result or "result" not in result:
            raise ValueError(f"RPC failed, capture remains incomplete: {result}")
        entries[role]={"id":calls,"method":method,"params":params,"request":request_name,"response":response_name,
                       "request_sha256":sha(encoded),"response_sha256":sha(raw)}
        return result["result"]
    started=datetime.now(timezone.utc).isoformat()
    version=rpc("version","getVersion",[]); genesis=rpc("genesis","getGenesisHash",[])
    finalized=rpc("root_before","getSlot",[{"commitment":"finalized"}])
    start=finalized-32-count+1 if start is None else start
    end=start+count-1
    if type(start) is not int or start<0 or end>finalized: raise ValueError("range beyond finalized root")
    slots=rpc("index_before","getBlocks",[start,end,{"commitment":"finalized"}])
    if not slots or slots!=sorted(set(slots)) or any(type(s) is not int or not start<=s<=end for s in slots):
        raise ValueError("empty/invalid source block index")
    blocks=[]
    for slot in slots:
        block=rpc(f"block-{slot}","getBlock",[slot,CONFIG])
        if not isinstance(block,dict): raise ValueError("listed block is null/missing")
        blocks.append({"slot":slot,"role":f"block-{slot}","blockhash":block["blockhash"]})
    first_raw=parse((root/entries[blocks[0]["role"]]["response"]).read_bytes())["result"]
    anchor_slot=first_raw["parentSlot"]
    anchor=rpc("anchor","getBlock",[anchor_slot,{**CONFIG,"transactionDetails":"none"}])
    if not isinstance(anchor,dict) or anchor["blockhash"]!=first_raw["previousBlockhash"]:
        raise ValueError("predecessor anchor mismatch")
    if rpc("index_after","getBlocks",[start,end,{"commitment":"finalized"}])!=slots:
        raise ValueError("source block index changed")
    if rpc("root_after","getSlot",[{"commitment":"finalized"}])<end or rpc("genesis_after","getGenesisHash",[])!=genesis:
        raise ValueError("source root/cluster changed")
    manifest={"schema":SCHEMA,"projection": "sof-runtime.solana-projection.v0","capture_kind":"rpc_capture",
              "source":endpoint,"commitment":"finalized","config":CONFIG,"genesis":genesis,"server_version":version,
              "start_slot":start,"end_slot":end,"listed_blocks":blocks,"anchor":{"slot":anchor_slot,"blockhash":anchor["blockhash"]},
              "rpc":entries,"started_utc":started,"completed_utc":datetime.now(timezone.utc).isoformat(),
              "finality_independently_verified":False}
    with (root/"manifest.json").open("xb") as stream: stream.write(canonical(manifest))
    return manifest


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir",required=True,type=Path); parser.add_argument("--endpoint",default="https://api.devnet.solana.com")
    parser.add_argument("--start-slot",type=int); parser.add_argument("--count",type=int,default=3)
    args=parser.parse_args(); result=capture(args.output_dir,args.endpoint,args.start_slot,args.count)
    print(canonical({"status":"CAPTURED_LOCAL","source":result["source"],"range":[result["start_slot"],result["end_slot"]],"blocks":len(result["listed_blocks"]),"server_version":result["server_version"]}).decode())
