"""Source-row Python/Fraction and SciPy controls, not Rust packet algorithms."""
from __future__ import annotations

from fractions import Fraction
from time import perf_counter

import numpy as np


def exact_action(source, signs, vector, update=False):
    x = [Fraction(int(a),int(b)) for a,b in vector]
    result = [Fraction(0) for _ in x]
    for s,value in enumerate(x):
        if not value or signs[s] == 0:
            continue
        start,stop = source.indptr[s:s+2]
        mass = sum(int(v) for v in source.data[start:stop])
        for at in range(start,stop):
            result[int(source.indices[at])] += value*Fraction(int(signs[s])*int(source.data[at]),mass)
    if update:
        result = [(4*old+min(Fraction(1),max(Fraction(0),drive)))/5 for old,drive in zip(x,result)]
    return [[str(v.numerator),str(v.denominator)] for v in result]


def exact_run(source,signs,vector,operation,iterations):
    state = vector
    for _ in range(iterations):
        state=exact_action(source,signs,state if operation=="update" else vector,operation=="update")
    return state


def source_numeric(source,signs):
    started = perf_counter()
    matrix = source.astype(np.float64)
    mass = np.asarray(source.sum(axis=1)).ravel()
    for row in range(len(signs)):
        if mass[row]:
            matrix.data[matrix.indptr[row]:matrix.indptr[row+1]] *= int(signs[row])/float(mass[row])
    return matrix,perf_counter()-started


def numeric_run(matrix,x,operation,iterations):
    state=x.copy()
    for _ in range(iterations):
        drive=matrix@state if operation=="update" else matrix@x
        state=0.8*state+0.2*np.clip(drive,0,1) if operation=="update" else drive
    if not np.all(np.isfinite(state)):
        raise ValueError("nonfinite SciPy output")
    return state


def compare(reference,actual):
    reference=np.asarray(reference,dtype=np.float64); actual=np.asarray(actual,dtype=np.float64)
    if reference.shape != actual.shape or not np.all(np.isfinite(actual)) or not np.all(np.isfinite(reference)):
        raise ValueError("nonfinite or wrong-sized numerical output")
    error=np.abs(actual-reference)
    scale=1e-12+1e-12*np.abs(reference)
    fate=lambda x:np.where(x<=0,0,np.where(x>=1,2,1))
    return {"accepted":bool(np.all(error<=scale)),"max_absolute_error":float(np.max(error,initial=0)),
            "max_scaled_error":float(np.max(error/scale,initial=0)),"l1_error":float(np.sum(error)),
            "l2_error":float(np.linalg.norm(error)),"output_0_1_region_disagreements":int(np.count_nonzero(fate(actual)!=fate(reference)))}
