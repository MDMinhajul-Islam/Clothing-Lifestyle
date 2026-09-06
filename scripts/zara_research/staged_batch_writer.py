"""Staged Batch Writer & Indexed Data Manager for Zara US Product Detail Enrichment.

Eliminates master file rewrite thrashing and linear table scans:
1. Maintains in-memory indexes (products_by_id, variants_by_product_id, etc.) with O(1) updates.
2. Per-product: writes raw audit evidence and appends a lightweight checkpoint journal record.
3. Every N products (default 25-50) or at batch boundary: atomically flushes flattened master tables.
"""

import json
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple


def atomic_write_json(path: Path, data: Any) -> None:
    """Atomically write data as JSON using a temporary file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + '.tmp')
    tmp_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    tmp_path.replace(path)


class StagedBatchManager:
    """Manages indexed product entities in memory with periodic staged atomic flushing."""

    def __init__(self, state_dir: Path, raw_dir: Path, flush_interval: int = 50):
        self.state_dir = Path(state_dir)
        self.raw_dir = Path(raw_dir)
        self.flush_interval = flush_interval

        # Journal file path
        self.journal_path = self.raw_dir / 'checkpoints' / 'enrichment_journal.jsonl'
        self.journal_path.parent.mkdir(parents=True, exist_ok=True)

        # In-memory indexes for O(1) access and updates
        self.products_by_id: Dict[str, Dict[str, Any]] = {}
        self.queue_by_id: Dict[str, Dict[str, Any]] = {}
        self.variants_by_product_id: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.colors_by_product_id: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.images_by_product_id: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.price_history_by_product_id: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

        self.pending_unflushed_count = 0
        self.total_processed_count = 0
        self.total_flushes = 0
        self.cumulative_persistence_time = 0.0

        self._load_master_indexes()

    def _load_master_indexes(self) -> None:
        """Load existing master tables into memory indexes once at initialization."""
        t0 = time.perf_counter()

        q_path = self.state_dir / 'product_detail_queue.json'
        p_path = self.state_dir / 'product_details.json'
        v_path = self.state_dir / 'product_variants.json'
        c_path = self.state_dir / 'product_colors.json'
        i_path = self.state_dir / 'product_images.json'
        h_path = self.state_dir / 'product_price_history.json'

        if q_path.exists():
            for item in json.loads(q_path.read_text(encoding='utf-8')):
                self.queue_by_id[item['id']] = item

        if p_path.exists():
            for p in json.loads(p_path.read_text(encoding='utf-8')):
                self.products_by_id[p['product_id']] = p

        if v_path.exists():
            for v in json.loads(v_path.read_text(encoding='utf-8')):
                self.variants_by_product_id[v['product_id']].append(v)

        if c_path.exists():
            for c in json.loads(c_path.read_text(encoding='utf-8')):
                self.colors_by_product_id[c['product_id']].append(c)

        if i_path.exists():
            for img in json.loads(i_path.read_text(encoding='utf-8')):
                self.images_by_product_id[img['product_id']].append(img)

        if h_path.exists():
            for h in json.loads(h_path.read_text(encoding='utf-8')):
                self.price_history_by_product_id[h['product_id']].append(h)

        print(f"Loaded master indexes in {(time.perf_counter()-t0)*1000:.1f}ms: "
              f"{len(self.products_by_id)} prods, {sum(len(v) for v in self.variants_by_product_id.values())} vars, "
              f"{sum(len(c) for c in self.colors_by_product_id.values())} cols, "
              f"{sum(len(i) for i in self.images_by_product_id.values())} imgs.")

    def stage_product_enrichment(
        self,
        product_id: str,
        prod_rec: Dict[str, Any],
        vars_rec: List[Dict[str, Any]],
        cols_rec: List[Dict[str, Any]],
        imgs_rec: List[Dict[str, Any]],
        price_rec: Optional[Dict[str, Any]],
        raw_evidence: Dict[str, Any],
        queue_item: Dict[str, Any]
    ) -> Tuple[bool, float]:
        """Stage an enriched product's records with O(1) index updates.
        
        Per-product actions:
        1. Write raw audit evidence file.
        2. Append checkpoint journal entry.
        3. Update in-memory indexes.
        
        Returns:
            (flushed_to_master: bool, per_product_write_time_sec: float)
        """
        t0 = time.perf_counter()

        # 1. Immediate individual raw audit evidence write
        raw_target = self.raw_dir / 'product_details' / f"{product_id.replace(':', '_')}.json"
        atomic_write_json(raw_target, raw_evidence)

        # 2. Append to checkpoint journal (lightweight append-only)
        journal_entry = {
            "product_id": product_id,
            "status": queue_item.get("status", "COMPLETE"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "content_hash": prod_rec.get("source_content_hash"),
            "current_price": prod_rec.get("current_price"),
            "variants_count": len(vars_rec),
            "colors_count": len(cols_rec),
            "images_count": len(imgs_rec)
        }
        with open(self.journal_path, "a", encoding="utf-8") as jf:
            jf.write(json.dumps(journal_entry, ensure_ascii=False) + "\n")

        # 3. O(1) in-memory index updates
        self.products_by_id[product_id] = prod_rec
        self.variants_by_product_id[product_id] = vars_rec
        self.colors_by_product_id[product_id] = cols_rec
        self.images_by_product_id[product_id] = imgs_rec
        if price_rec:
            # Avoid duplicate price history records for same timestamp
            hist_list = self.price_history_by_product_id[product_id]
            if not any(h.get("history_id") == price_rec.get("history_id") for h in hist_list):
                hist_list.append(price_rec)
        self.queue_by_id[product_id] = queue_item

        self.pending_unflushed_count += 1
        self.total_processed_count += 1
        write_time = time.perf_counter() - t0

        # 4. Check periodic flush threshold
        flushed = False
        if self.pending_unflushed_count >= self.flush_interval:
            flush_stats = self.flush()
            flushed = True

        return flushed, write_time

    def flush(self) -> Dict[str, Any]:
        """Flatten in-memory indexes and atomically overwrite master datasets."""
        if self.pending_unflushed_count == 0:
            return {"flushed_products": 0, "flush_duration_sec": 0.0}

        t0 = time.perf_counter()

        q_path = self.state_dir / 'product_detail_queue.json'
        p_path = self.state_dir / 'product_details.json'
        v_path = self.state_dir / 'product_variants.json'
        c_path = self.state_dir / 'product_colors.json'
        i_path = self.state_dir / 'product_images.json'
        h_path = self.state_dir / 'product_price_history.json'

        # Flatten indexes
        flattened_queue = list(self.queue_by_id.values())
        flattened_prods = list(self.products_by_id.values())
        flattened_vars = [v for sublist in self.variants_by_product_id.values() for v in sublist]
        flattened_cols = [c for sublist in self.colors_by_product_id.values() for c in sublist]
        flattened_imgs = [img for sublist in self.images_by_product_id.values() for img in sublist]
        flattened_hist = [h for sublist in self.price_history_by_product_id.values() for h in sublist]

        # Atomic writes
        atomic_write_json(q_path, flattened_queue)
        atomic_write_json(p_path, flattened_prods)
        atomic_write_json(v_path, flattened_vars)
        atomic_write_json(c_path, flattened_cols)
        atomic_write_json(i_path, flattened_imgs)
        atomic_write_json(h_path, flattened_hist)

        flush_duration = time.perf_counter() - t0
        flushed_count = self.pending_unflushed_count
        self.pending_unflushed_count = 0
        self.total_flushes += 1
        self.cumulative_persistence_time += flush_duration

        print(f"[Master Flush #{self.total_flushes}] Merged {flushed_count} products ({len(flattened_prods)} total in catalogue) in {flush_duration*1000:.1f}ms")

        return {
            "flushed_products": flushed_count,
            "flush_duration_sec": round(flush_duration, 3),
            "total_catalogue_products": len(flattened_prods),
            "flush_count": self.total_flushes
        }
