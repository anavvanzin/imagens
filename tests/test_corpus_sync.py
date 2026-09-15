import json
import tempfile
import unittest
from pathlib import Path

from scripts.corpus_sync import (
    build_constellations,
    generate,
    normalize_url,
    resolve_entry,
    transform_item,
    validate_publication,
    validate_records,
    write_outputs,
)

ROOT = Path(__file__).resolve().parents[1]


class CorpusSyncTests(unittest.TestCase):
    def setUp(self):
        self.corpus = [{
            "id": "uuid-1", "title": "Justice", "country": "France",
            "date": "1900", "regime": "normativo", "motif": ["Balança"],
            "url": "https://example.test/item.item", "citation_abnt": "Citação.",
        }]
        self.legacy = [{
            "id": "FR-OLD", "title": "Justice antiga", "country": "France",
            "date": "1900", "regime": "normativo", "motif": [],
            "url": "http://example.test/item/",
        }]

    def test_transform_uses_editorial_image_and_keeps_legacy_alias(self):
        result = transform_item(self.corpus[0], {
            "canonical_id": "uuid-1", "legacy_ids": ["FR-OLD"],
            "image": {"path": "assets/acervo/uuid-1.webp", "license": "PD", "credit": "Arquivo"},
            "public_analysis": {"summary": "Leitura."},
        })
        self.assertEqual(result["pais"], "França")
        self.assertEqual(result["imagem"], "assets/acervo/uuid-1.webp")
        self.assertEqual(result["legacy_ids"], ["FR-OLD"])
        self.assertEqual(result["analise_publica"]["summary"], "Leitura.")

    def test_resolve_order_id_then_url_then_alias(self):
        source, item_id = resolve_entry({"canonical_id": "uuid-1"}, self.corpus, self.legacy)
        self.assertEqual((source["title"], item_id), ("Justice", "uuid-1"))
        source, item_id = resolve_entry({"canonical_id": "missing", "source_url": "http://example.test/item/"}, self.corpus, self.legacy)
        self.assertEqual(item_id, "uuid-1")
        source, item_id = resolve_entry({"canonical_id": "missing", "legacy_ids": ["FR-OLD"]}, self.corpus, self.legacy)
        self.assertEqual(item_id, "uuid-1")

    def test_resolve_never_matches_title(self):
        with self.assertRaisesRegex(ValueError, "sem correspondência"):
            resolve_entry({"canonical_id": "missing", "overrides": {"title": "Justice"}}, self.corpus, self.legacy)

    def test_new_published_item_requires_complete_gate(self):
        with self.assertRaisesRegex(ValueError, "faltam"):
            validate_publication({"corpus_commit": "abc", "items": [{
                "canonical_id": "uuid-1", "editorial_status": "published",
            }]})

    def test_grandfathered_item_may_lack_image(self):
        validate_publication({"corpus_commit": "abc", "items": [{
            "legacy_record_id": "FR-OLD", "editorial_status": "published", "grandfathered": True,
        }]})

    def test_new_published_item_rejects_hotlink_as_primary_image(self):
        with self.assertRaisesRegex(ValueError, "image.path local"):
            validate_publication({"corpus_commit": "abc", "items": [{
                "canonical_id": "uuid-1", "editorial_status": "published",
                "approved_by": "ana", "approved_at": "2026-09-15",
                "image": {
                    "path": "https://example.test/image.jpg", "source_url": "https://example.test/image.jpg",
                    "license": "PD", "credit": "Arquivo", "alt": "Descrição",
                },
            }]})

    def test_generate_emits_review_only_in_preview(self):
        publication = {
            "corpus_commit": "abc",
            "generated_at": "2026-09-15",
            "items": [{"canonical_id": "uuid-1", "editorial_status": "review"}],
            "constellations": [{
                "slug": "teste", "title": "Teste", "editorial_status": "review", "item_ids": ["uuid-1"],
            }],
        }
        items, stats, constellations = generate(self.corpus, publication, self.legacy)
        self.assertEqual((items, stats["total"], constellations), ([], 0, []))
        items, stats, constellations = generate(self.corpus, publication, self.legacy, include_review=True)
        self.assertEqual((len(items), stats["total"], constellations[0]["item_ids"]), (1, 1, ["uuid-1"]))

    def test_constellation_preserves_declared_order(self):
        items = [{"id": "b"}, {"id": "a"}]
        result = build_constellations([{
            "slug": "x", "editorial_status": "published", "item_ids": ["a", "b", "missing"],
        }], items)
        self.assertEqual(result[0]["item_ids"], ["a", "b"])

    def test_url_normalization(self):
        self.assertEqual(normalize_url("http://example.test/x.item/"), "https://example.test/x")

    def test_validation_rejects_duplicate_ids(self):
        records = [self.corpus[0], {**self.corpus[0]}]
        with self.assertRaisesRegex(ValueError, "ID duplicado"):
            validate_records(records, Path("/does/not/exist"))

    def test_manifest_preserves_95_and_stages_indivisible_batch(self):
        publication = json.loads((ROOT / "site/data/publication.json").read_text())
        published = [item for item in publication["items"] if item["editorial_status"] == "published"]
        review = [item for item in publication["items"] if item["editorial_status"] == "review"]
        self.assertEqual(len(published), 95)
        self.assertEqual(len(review), 8)
        self.assertTrue(all(item.get("grandfathered") for item in published))
        self.assertEqual(publication["constellations"][0]["item_ids"], [item["canonical_id"] for item in review])

    def test_public_analysis_never_contains_composite(self):
        publication = json.loads((ROOT / "site/data/publication.json").read_text())
        for item in publication["items"]:
            analysis = item.get("public_analysis") or {}
            self.assertNotIn("purificacao_composto", json.dumps(analysis))
            self.assertNotIn("endurecimento_score", json.dumps(analysis))

    def test_generated_outputs_are_idempotent(self):
        items, stats, constellations = generate(self.corpus, {
            "corpus_commit": "abc", "generated_at": "2026-09-15",
            "items": [{"canonical_id": "uuid-1", "editorial_status": "review"}],
            "constellations": [],
        }, self.legacy, include_review=True)
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            write_outputs(out, items, stats, constellations)
            first = {path.name: path.read_bytes() for path in out.iterdir()}
            write_outputs(out, items, stats, constellations)
            self.assertEqual(first, {path.name: path.read_bytes() for path in out.iterdir()})


if __name__ == "__main__":
    unittest.main()
