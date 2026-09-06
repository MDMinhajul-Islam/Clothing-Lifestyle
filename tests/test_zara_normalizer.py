import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/zara_research/normalize.py'
spec = importlib.util.spec_from_file_location('normalizer', SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class NormalizerTests(unittest.TestCase):
    def test_rejects_nonfinite_and_negative_prices(self):
        for price in ['NaN', 'Infinity', '-0.01']:
            with self.assertRaises(ValueError):
                module.money(price)

    def test_preserves_missing_price(self):
        self.assertIsNone(module.money(None))
        self.assertEqual(module.money('59.9'), '59.90')

    def test_graph_unwrap_does_not_promote_variants_to_groups(self):
        graph = {'@graph': [{'@type': 'ProductGroup', 'hasVariant': [{'@type': 'Product'}]}]}
        result = list(module.objects(graph))
        self.assertEqual(len(result), 2)
        self.assertEqual(result[1]['@type'], 'ProductGroup')


if __name__ == '__main__':
    unittest.main()
