"""Exact/numerical parity and hostile input controls for the new kernel."""
from copy import deepcopy
import json
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest

import numpy as np
from scipy import sparse

from applications.malecns_sparse_kernel.protocol import (
    arrays_from_source,canonical,file_sha,numerical_matrix,read_packet,write_packet,
)
from applications.malecns_sparse_kernel.reference import compare,exact_run,numeric_run,source_numeric
from applications.malecns_sparse_kernel.runner import binary,build,request,run


class SparseKernelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): build()

    def fixture(self,directory):
        source=sparse.csr_matrix(np.array([[0,2,1,0,0],[0,0,0,1,0],[3,0,0,1,0],[0,0,0,0,0],[1,0,2,0,0]],dtype=np.int64))
        signs=np.array([1,-1,1,0,-1],dtype=np.int8)
        _,arrays,_=arrays_from_source(source,signs)
        packet=Path(directory)/"matrix.bin"
        write_packet(packet,arrays,{"fixture":"mixed-sign-empty-row"})
        return source,signs,arrays,packet

    def reject(self,raw,directory,name):
        path=Path(directory)/f"bad-{name}.json"; path.write_bytes(canonical(raw))
        process=subprocess.run([str(binary()),str(path)],capture_output=True,timeout=30)
        self.assertNotEqual(process.returncode,0,process.stdout)
        self.assertEqual(json.loads(process.stdout)["status"],"UNRESOLVED")

    def test_source_transpose_and_target_rows_agree(self):
        with tempfile.TemporaryDirectory() as directory:
            source,signs,arrays,packet=self.fixture(directory)
            _,decoded=read_packet(packet,file_sha(packet))
            for a,b in zip(arrays,decoded): self.assertTrue(np.array_equal(a,b))
            matrix,_=source_numeric(source,signs); target=numerical_matrix(decoded)
            x=np.array([1.,.25,.5,.75,1.])
            for operation in ("spmv","update"):
                expected=numeric_run(matrix.T,x,operation,3)
                self.assertTrue(compare(expected,numeric_run(target,x,operation,3))["accepted"])
                outputs=[]
                for threads in (1,2,4):
                    result,_=run(request(packet,file_sha(packet),x.tolist(),operation=operation,threads=threads,iterations=3),directory,f"{operation}-{threads}")
                    self.assertTrue(compare(expected,result["output"])["accepted"])
                    outputs.append(np.array(result["output"]))
                for actual in outputs[1:]: self.assertTrue(np.array_equal(outputs[0].view(np.uint64),actual.view(np.uint64)))

    def test_exact_multistep_rationals_and_parallel_parity(self):
        with tempfile.TemporaryDirectory() as directory:
            source,signs,_,packet=self.fixture(directory)
            vector=[["1","1"],["1","3"],["2","7"],["0","1"],["1","5"]]
            for operation in ("spmv","update"):
                expected=exact_run(source,signs,vector,operation,4)
                for threads in (1,4):
                    result,_=run(request(packet,file_sha(packet),vector,"exact",operation,threads,4),directory,f"exact-{operation}-{threads}")
                    self.assertEqual(result["output"],expected)

    def test_exact_clipping_does_not_round_tiny_perturbations(self):
        with tempfile.TemporaryDirectory() as directory:
            source=sparse.csr_matrix(np.array([[0,0,1],[0,0,1],[0,0,0]],dtype=np.int64))
            signs=np.array([1,1,0],dtype=np.int8); _,arrays,_=arrays_from_source(source,signs)
            packet=Path(directory)/"matrix.bin"; write_packet(packet,arrays,{"fixture":"clipping-threshold"})
            denominator=str(2**100)
            for name,numerator in (("above","1"),("below","-1")):
                vector=[["1","1"],[numerator,denominator],["0","1"]]
                expected=exact_run(source,signs,vector,"update",1)
                result,_=run(request(packet,file_sha(packet),vector,"exact","update"),directory,name)
                self.assertEqual(result["output"],expected)
            self.assertNotEqual(exact_run(source,signs,[["1","1"],["-1",denominator],["0","1"]],"update",1)[2],["1","5"])

    def test_signed_cancellation_and_zero_matrix(self):
        with tempfile.TemporaryDirectory() as directory:
            source=sparse.csr_matrix(np.array([[0,0,1],[0,0,1],[0,0,0]],dtype=np.int64))
            for name,signs in (("cancel",np.array([1,-1,0],dtype=np.int8)),("empty",np.zeros(3,dtype=np.int8))):
                if name=="empty": source=sparse.csr_matrix((3,3),dtype=np.int64)
                _,arrays,_=arrays_from_source(source,signs); packet=Path(directory)/f"{name}.bin"
                write_packet(packet,arrays,{"fixture":name})
                vector=[["1","1"]]*3
                result,_=run(request(packet,file_sha(packet),vector,"exact"),directory,name)
                self.assertEqual(result["output"],[["0","1"]]*3)

    def test_truncated_trailing_header_and_checksum_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            _,_,_,packet=self.fixture(directory); original=packet.read_bytes()
            for name,raw in (("truncated",original[:-1]),("trailing",original+b"x"),("header",b"INVALID!"+original[8:]),("damage",original[:-1]+b"\xff")):
                changed=Path(directory)/f"{name}.bin"; changed.write_bytes(raw)
                self.reject(request(changed,file_sha(changed),[0.]*5),directory,name)
                with self.assertRaises((ValueError,KeyError)): read_packet(changed,file_sha(changed))
            self.reject(request(packet,"0"*64,[0.]*5),directory,"sha")

    def test_invalid_structure_with_matching_hash_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            _,_,_,packet=self.fixture(directory); raw=packet.read_bytes()
            length=struct.unpack_from("<I",raw,8)[0]; at=12+length
            for name,offset,data in (("pointer",at,struct.pack("<Q",1)),("source",at+6*8,struct.pack("<I",5)),
                                     ("weight",at+6*8+7*4,struct.pack("<I",0)),
                                     ("duplicate",at+6*8+4,struct.pack("<I",2)),
                                     ("mass",len(raw)-5*8,struct.pack("<Q",99)),
                                     ("unknown-sign",len(raw)-5*8-5+2,b"\x00")):
                changed=bytearray(raw); changed[offset:offset+len(data)]=data
                other=Path(directory)/f"{name}.bin"; other.write_bytes(changed)
                self.reject(request(other,file_sha(other),[0.]*5),directory,name)
            header,arrays=read_packet(packet,file_sha(packet))
            modified=list(arrays); modified[4]=modified[4].copy(); modified[4][0]+=1
            with self.assertRaises(ValueError): write_packet(Path(directory)/"mass.bin",modified,{})

    def test_invalid_modes_vector_dimensions_arithmetic_and_limits(self):
        with tempfile.TemporaryDirectory() as directory:
            _,_,_,packet=self.fixture(directory); base=request(packet,file_sha(packet),[0.]*5)
            cases=[]
            for key,value in (("mode","approximate-exact"),("operation","other"),("threads",0),("iterations",0),("repeats",0),("warmups",3),("vector",[0.])):
                raw=deepcopy(base); raw[key]=value; cases.append(raw)
            exact=deepcopy(base); exact["mode"]="exact"; cases.append(exact)
            exact=deepcopy(base); exact["mode"]="exact"; exact["vector"]=[["1","0"]]*5; cases.append(exact)
            exact=deepcopy(base); exact["mode"]="exact"; exact["vector"]=[["1","1"]]*5; exact["iterations"]=5; cases.append(exact)
            exact=deepcopy(base); exact["mode"]="exact"; exact["vector"]=[["9"*8192,"1"]]*5; cases.append(exact)
            overflow=deepcopy(base); overflow["operation"]="update"; overflow["vector"]=[0.,0.,1.7e308,0.,-1.7e308]; cases.append(overflow)
            for i,raw in enumerate(cases): self.reject(raw,directory,str(i))


if __name__=="__main__": unittest.main()
