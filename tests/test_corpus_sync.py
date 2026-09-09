import json
import tempfile
import unittest
from pathlib import Path

from scripts.corpus_sync import build_stats, transform_item, validate_records


class CorpusSyncTests(unittest.TestCase):
    def test_transform_prefers_public_thumbnail_over_unpublished_local_path(self):
        item = {
            "id": "BR-001", "title": "Justice", "country": "Brazil",
            "date": "1900", "regime": "normativo", "motif": ["female allegory", "Balança"],
            "local_image_path": "corpus/imagens/BR/BR-001.jpg",
            "thumbnail_url": "https://example.test/image.jpg",
            "endurecimento_score": 0.5, "indicadores": {"rigidez_postural": 2}
        }
        result = transform_item(item)
        self.assertEqual(result["pais"], "Brasil")
        self.assertEqual(result["imagem"], "https://example.test/image.jpg")
        self.assertEqual(result["motivos"], ["Balança"])
        self.assertEqual(result["endurecimento_score"], 0.5)

    def test_transform_keeps_site_serveable_local_image(self):
        item = {
            "id": "uuid-1", "title": "Justice", "country": "France",
            "date": "1900", "regime": "normativo",
            "local_image_path": "assets/justice.webp",
        }
        result = transform_item(item)
        self.assertEqual(result["imagem"], "assets/justice.webp")
        self.assertTrue(result["tem_imagem"])

    def test_unpublished_local_path_alone_is_not_an_image(self):
        item = {
            "id": "DE-001", "title": "Justitia", "country": "Germany",
            "date": "1543", "regime": "normativo",
            "local_image_path": "corpus/imagens/DE/DE-001.jpg",
            "thumbnail_url": "",
        }
        result = transform_item(item)
        self.assertEqual(result["imagem"], "")
        self.assertFalse(result["tem_imagem"])

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
