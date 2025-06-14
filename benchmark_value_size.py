#!/usr/bin/env python3
"""
Benchmark 1 (versión ligera) – Latencia vs. Tamaño del valor
Tamaños: 512 B, 4 KB, 512 KB, 1 MB, 4 MB
Carga A: 100 % get
Carga B: 50 % set / 50 % get
Por defecto: 300 operaciones por tamaño.
"""

import csv, random, string, time
from statistics import mean, quantiles

import grpc
import kvstore_pb2 as pb
import kvstore_pb2_grpc as pbg

VALUE_SIZES   = [512, 4*1024, 512*1024, 1*1024*1024, 4*1024*1024]
OPS_DEFAULT   = 100          # <- ahora 300
WARMUP_SETS   = 20           # <- antes 200
SERVER_ADDR   = "127.0.0.1:50051"
CSV_FILE      = "benchmark_size_latency.csv"


# utilidades ──────────────────────────────────────────────
def rkey(n=16): return "".join(random.choices(string.ascii_letters+string.digits, k=n))
def value(sz):   return "x"*sz

def warm(stub, sz):
    v = value(sz)
    for _ in range(WARMUP_SETS):
        stub.set(pb.KeyValue(key=rkey(), value=v))

def bench(stub, sz, n_ops, read_only):
    v = value(sz)
    lat=[]
    for i in range(n_ops):
        is_get = read_only or (i & 1)
        if is_get:
            k=rkey(); stub.set(pb.KeyValue(key=k,value=v))
            t=time.perf_counter_ns(); stub.get(pb.Key(key=k))
        else:
            k=rkey(); t=time.perf_counter_ns(); stub.set(pb.KeyValue(key=k,value=v))
        lat.append((time.perf_counter_ns()-t)/1_000_000)
    return lat
# ─────────────────────────────────────────────────────────

def main(n_ops):
    with grpc.insecure_channel(SERVER_ADDR) as ch:
        grpc.channel_ready_future(ch).result(timeout=5)
        stub=pbg.KVStoreStub(ch)
        rows=[]
        for sz in VALUE_SIZES:
            print(f"\n📦 {sz/1024:.1f} KB  ({sz} B)")
            warm(stub,sz)
            for name,ro in (("soloLectura",True),("mixto50/50",False)):
                l=bench(stub,sz,n_ops,ro)
                p50,p95=quantiles(l,n=100)[49],quantiles(l,n=20)[18]
                print(f"   {name:<12} n={n_ops:3} avg={mean(l):6.2f} ms  "
                      f"p50={p50:6.2f} ms  p95={p95:6.2f} ms")
                rows.append(dict(value_size_bytes=sz,workload=name,
                                 avg_ms=f"{mean(l):.3f}",p50_ms=f"{p50:.3f}",
                                 p95_ms=f"{p95:.3f}",n_ops=n_ops))
    with open(CSV_FILE,"w",newline="") as f:
        csv.DictWriter(f,fieldnames=rows[0].keys()).writeheader(); f.writerows(rows)
    print(f"\n💾 Resultados guardados en {CSV_FILE}")

if __name__=="__main__":
    import argparse, csv
    ap=argparse.ArgumentParser()
    ap.add_argument("--ops",type=int,default=OPS_DEFAULT,
                    help=f"Operaciones por tamaño (default {OPS_DEFAULT})")
    main(ap.parse_args().ops)