# Phase 1C Comprehensive Concurrency & Throughput Benchmark Report

**Date**: 2026-09-06T17:22:25.990099+00:00
**Dataset**: 100 Identical Validated Zara US Products

### 1. Benchmark Configurations Summary Table

| Configuration | Concurrency | Wall Time (s) | E2E (s/prod) | Throughput (pages/s) | Nav (ms) | Ready (ms) | Parse (ms) | Norm (ms) | Persist (ms) | Speedup vs Baseline |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Config A: Baseline 1-Worker** | 1 | 569.72 | 5.7 | 0.18 | 919.2 | 3940.4 | 676.8 | 0.7 | 18.6 | **1.0x** |
| **Config B: Optimized 1-Worker** | 1 | 246.08 | 2.5 | 0.41 | 1239.4 | 487.8 | 468.0 | 0.7 | 2.2 | **2.32x** |
| **Config C: Optimized 2-Worker** | 2 | 229.35 | 4.0 | 0.44 | 2676.2 | 611.5 | 532.0 | 0.8 | 2.5 | **2.48x** |
| **Config D: Optimized 4-Worker** | 4 | 142.87 | 4.1 | 0.7 | 2010.5 | 1000.1 | 510.6 | 0.6 | 2.1 | **3.99x** |
| **Config E: Optimized 6-Worker** | 6 | 134.14 | 5.5 | 0.75 | 2920.9 | 1435.1 | 488.6 | 0.7 | 2.2 | **4.25x** |

### 2. CTO Target Assessment (~1,000 Products in ~5 Minutes / ~3.33 pages/sec)

- **Config A: Baseline 1-Worker**: 92.59 mins for 1,000 products (0.18 pages/s) — Target Met: **NO**
- **Config B: Optimized 1-Worker**: 40.65 mins for 1,000 products (0.41 pages/s) — Target Met: **NO**
- **Config C: Optimized 2-Worker**: 37.88 mins for 1,000 products (0.44 pages/s) — Target Met: **NO**
- **Config D: Optimized 4-Worker**: 23.81 mins for 1,000 products (0.7 pages/s) — Target Met: **NO**
- **Config E: Optimized 6-Worker**: 22.22 mins for 1,000 products (0.75 pages/s) — Target Met: **NO**

### 3. Accuracy Gate Summary
- Total products audited: 99
- Identity parity: 99/99
- Canonical URL parity: 99/99
- Current price parity: 99/99
- Variant count parity: 99/99
- Color count parity: 61/99
- Composition parity: 99/99
- Documented mismatches count: 38