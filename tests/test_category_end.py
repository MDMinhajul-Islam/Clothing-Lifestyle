import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('category_end', Path(__file__).resolve().parents[1] / 'scripts/zara_research/category_end.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class CategoryEndTests(unittest.TestCase):
    def settled(self, iteration, **changes):
        return dict(scroll_iteration=iteration, at_bottom=True, settled=True,
                    new_unique_products=0, products_seen=20, document_height=1000, **changes)

    def test_first_viewport_never_complete(self):
        self.assertIsNone(module.completion_reason([self.settled(0, explicit_end=True)]))

    def test_middle_stagnation_not_end(self):
        observations = [self.settled(i) for i in range(3)]
        observations[-1]['at_bottom'] = False
        self.assertIsNone(module.completion_reason(observations))

    def test_three_stable_post_scroll_checks(self):
        self.assertIsNone(module.completion_reason([self.settled(i) for i in range(3)]))
        self.assertEqual(module.completion_reason([self.settled(i) for i in range(4)]), 'NO_NEW_PRODUCTS')

    def test_loading_and_height_growth_prevent_completion(self):
        observations = [self.settled(i) for i in range(4)]
        observations[-1]['loading'] = True
        self.assertIsNone(module.completion_reason(observations))
        observations[-1]['loading'] = False
        observations[-1]['document_height'] = 2000
        self.assertIsNone(module.completion_reason(observations))

    def test_restriction_is_not_completion(self):
        self.assertEqual(module.completion_reason([dict(technical_restriction=True)]), 'TECHNICAL_RESTRICTION')


if __name__ == '__main__':
    unittest.main()
