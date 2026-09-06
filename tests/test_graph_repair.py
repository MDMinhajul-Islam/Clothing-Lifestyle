import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts/zara_research'))
from repair_graph import canonicalize, department


class GraphRepairTests(unittest.TestCase):
    def test_unverified_query_preserved(self):
        url = 'https://www.zara.com/us/en/man-shirts-l737.html?page=2'
        self.assertEqual(canonicalize(url), url)
        self.assertEqual(canonicalize(url, url.split('?')[0]), url)

    def test_variant_alias_needs_observation(self):
        url = 'https://www.zara.com/us/en/woman-beauty-makeup-l4414.html?v1=1881272'
        self.assertEqual(canonicalize(url), url)
        self.assertEqual(canonicalize(url, url.split('?')[0]), url.split('?')[0])

    def test_cross_path_or_host_canonical_not_merged(self):
        url = 'https://www.zara.com/us/en/a-l1.html'
        self.assertEqual(canonicalize(url, 'https://example.com/us/en/a-l1.html'), url)
        self.assertEqual(canonicalize(url, 'https://www.zara.com/us/en/b-l2.html'), url)

    def test_fragments_are_not_new_category(self):
        url = 'https://www.zara.com/us/en/kids-girl-l323.html'
        self.assertEqual(canonicalize(url+'#main'), url)

    def test_cross_department_precedence(self):
        self.assertEqual(department('https://www.zara.com/us/en/home-kids-new-in-l3974.html'), 'ZARA HOME')
        self.assertEqual(department('https://www.zara.com/us/en/woman-beauty-makeup-l4414.html'), 'BEAUTY')


if __name__ == '__main__':
    unittest.main()
