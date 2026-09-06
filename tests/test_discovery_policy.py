import unittest
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts/zara_research'))


class DiscoveryPolicyTests(unittest.TestCase):
    def test_queue_item_preserves_deferred_status(self):
        from repair_graph import read, STATE
        queue = read(STATE / 'category_discovery_queue.json', [])
        deferred = [q for q in queue if q['status'] == 'DEFERRED']
        active = [q for q in queue if q['status'] == 'QUEUED']
        complete = [q for q in queue if q['status'] == 'COMPLETE']

        self.assertGreater(len(deferred), 0, "Expected deferred SEO routes to be present")
        self.assertEqual(len(queue), len(deferred) + len(active) + len(complete))

    def test_edge_relations_include_breadcrumbs_and_subcategories(self):
        from repair_graph import read, STATE
        edges = read(STATE / 'category_edges.json', [])
        relations = {e['relation'] for e in edges}

        self.assertIn('BREADCRUMB_PARENT', relations)
        self.assertIn('RELATED_LINK', relations)

    def test_deferred_items_have_seo_reason(self):
        from repair_graph import read, STATE
        queue = read(STATE / 'category_discovery_queue.json', [])
        deferred = [q for q in queue if q['status'] == 'DEFERRED']
        for item in deferred:
            self.assertEqual(item.get('checkpoint', {}).get('deferred_reason'), 'SEO_KEYWORD_ROUTE')


if __name__ == '__main__':
    unittest.main()
