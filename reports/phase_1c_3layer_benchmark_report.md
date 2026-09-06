# Phase 1C: 3-Layer Architecture 50-Product Benchmark Report

**Date**: 2026-09-06 11:45:07 UTC  
**Speedup Factor**: **4.01x faster** (6.22s → 1.55s)  
**Accuracy Gate Status**: DIFFERENCES DETECTED (42)  

## Performance Benchmark
| Metric | Old Pipeline | New 3-Layer Pipeline | Improvement |
| :--- | :---: | :---: | :---: |
| **Average Time / Product** | 6.22s | **1.55s** | **4.01x speedup** |
| **Median Time / Product** | 6.20s | **1.4s** | — |
| **Browser Navigation Time** | ~5.8s | **1.29s** | Single `page.content()` call |
| **Local Parsing Time** | N/A (DOM IPC) | **256.7 ms** | Local BeautifulSoup in-memory |
| **Normalization Time** | ~400 ms | **0.6 ms** | Python memory processing |
| **Slowest Product** | 7.39s | **2.85s** (zara-us:04772385) | — |

## Accuracy Gate Summary
- **Identity Matches**: 50 / 50
- **Pricing Matches**: 43 / 50
- **Variant Count Matches**: 50 / 50
- **Color Count Matches**: 18 / 50
- **Image Count Matches**: 40 / 50
- **Content Matches**: 50 / 50

### Mismatch Details
- **zara-us:04772227**: {"colors": {"old_count": 4, "new_count": 2}}
- **zara-us:03152225**: {"colors": {"old_count": 4, "new_count": 2}}
- **zara-us:04772385**: {"colors": {"old_count": 4, "new_count": 2}}
- **zara-us:03152232**: {"colors": {"old_count": 4, "new_count": 2}}
- **zara-us:03152205**: {"colors": {"old_count": 6, "new_count": 2}, "images": {"old_count": 71, "new_count": 10}}
- **zara-us:04786296**: {"colors": {"old_count": 7, "new_count": 5}}
- **zara-us:04786307**: {"colors": {"old_count": 4, "new_count": 2}}
- **zara-us:04772386**: {"colors": {"old_count": 4, "new_count": 2}}
- **zara-us:07812332**: {"colors": {"old_count": 6, "new_count": 4}}
- **zara-us:07827777**: {"colors": {"old_count": 4, "new_count": 2}}
- **zara-us:07823330**: {"colors": {"old_count": 4, "new_count": 2}}
- **zara-us:07768109**: {"colors": {"old_count": 4, "new_count": 2}}
- **zara-us:02778332**: {"colors": {"old_count": 5, "new_count": 3}}
- **zara-us:01030731**: {"colors": {"old_count": 7, "new_count": 3}, "images": {"old_count": 74, "new_count": 10}}
- **zara-us:08281740**: {"colors": {"old_count": 9, "new_count": 5}, "images": {"old_count": 78, "new_count": 14}}
- **zara-us:03332310**: {"colors": {"old_count": 8, "new_count": 4}, "images": {"old_count": 76, "new_count": 12}}
- **zara-us:12000822**: {"colors": {"old_count": 4, "new_count": 2}}
- **zara-us:12355820**: {"colors": {"old_count": 4, "new_count": 2}}
- **zara-us:00029400**: {"colors": {"old_count": 4, "new_count": 2}}
- **zara-us:03411390**: {"colors": {"old_count": 4, "new_count": 2}}
- **zara-us:00108313**: {"colors": {"old_count": 7, "new_count": 5}}
- **zara-us:03715349**: {"colors": {"old_count": 4, "new_count": 2}}
- **zara-us:08073702**: {"colors": {"old_count": 6, "new_count": 2}, "images": {"old_count": 73, "new_count": 8}}
- **zara-us:01044102**: {"colors": {"old_count": 7, "new_count": 3}, "images": {"old_count": 73, "new_count": 7}}
- **zara-us:02582555**: {"colors": {"old_count": 7, "new_count": 3}, "images": {"old_count": 70, "new_count": 6}}
- **zara-us:03153780**: {"colors": {"old_count": 4, "new_count": 2}}
- **zara-us:05644903**: {"colors": {"old_count": 4, "new_count": 2}}
- **zara-us:08501535**: {"colors": {"old_count": 4, "new_count": 2}}
- **zara-us:01095888**: {"images": {"old_count": 71, "new_count": 4}}
- **zara-us:14016800**: {"colors": {"old_count": 3, "new_count": 1}}
- **zara-us:44326728**: {"colors": {"old_count": 4, "new_count": 2}}
- **zara-us:44115121**: {"colors": {"old_count": 4, "new_count": 2}}
- **zara-us:46191008**: {"colors": {"old_count": 4, "new_count": 2}}
- **zara-us:40406509**: {"images": {"old_count": 71, "new_count": 6}}
- **zara-us:40247043**: {"images": {"old_count": 68, "new_count": 6}}
- **zara-us:20110153**: {"pricing": {"old_price": "39.90", "new_price": "39.90", "old_sale": true, "new_sale": false}}
- **zara-us:20110392**: {"pricing": {"old_price": "39.90", "new_price": "39.90", "old_sale": true, "new_sale": false}}
- **zara-us:20110604**: {"pricing": {"old_price": "49.90", "new_price": "49.90", "old_sale": true, "new_sale": false}}
- **zara-us:20110820**: {"pricing": {"old_price": "69.90", "new_price": "69.90", "old_sale": true, "new_sale": false}}
- **zara-us:20110928**: {"pricing": {"old_price": "59.90", "new_price": "59.90", "old_sale": true, "new_sale": false}}
- **zara-us:20110966**: {"pricing": {"old_price": "59.90", "new_price": "59.90", "old_sale": true, "new_sale": false}}
- **zara-us:20120273**: {"pricing": {"old_price": "35.90", "new_price": "35.90", "old_sale": true, "new_sale": false}}