import json
import tempfile
import unittest
from pathlib import Path

from scripts.corpus_sync import build_stats, transform_item, validate_records


class CorpusSyncTests(unittest.TestCase):
    def test_transform_prefers_local_image_and_keeps_analysis(self):
        item = {
            "id": "uuid-1", "title": "Justice", "country": "France",
            "date": "1900", "regime": "normativo", "motif": ["female allegory", "Balança"],
            "local_image_path": "assets/justice.webp", "thumbnail_url": "https://example.test/image",
            "endurecimento_score": 0.5, "indicadores": {"rigidez_postural": 2}
        }
        result = transform_item(item)
        self.assertEqual(result["pais"], "França")
        self.assertEqual(result["imagem"], "assets/justice.webp")
        self.assertEqual(result["motivos"], ["Balança"])
        self.assertEqual(result["endurecimento_score"], 0.5)

    def test_validation_rejects_duplicate_ids(self):
        records = [{"id": "same", "title": "A", "country": "Brazil", "date": "1900", "regime": "militar"},
                   {"id": "same", "title": "B", "country": "Brazil", "date": "1901", "regime": "militar"}]
        with self.assertRaisesRegex(ValueError, "ID duplicado"):
            validate_records(records, Path("/does/not/exist"))

    def test_stats_count_published_items_only(self):
        items = [transform_item({
            "id": "a", "title": "A", "country": "Brazil", "date": "1900",
            "regime": "militar", "motif": ["Espada"]
        })]
        stats = build_stats(items, 2, "test")
        self.assertEqual(stats["total"], 1)
        self.assertEqual(stats["meta"]["source_count"], 2)


if __name__ == "__main__":
    unittest.main()
