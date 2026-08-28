# Schema-First Sync Pipeline: ICONOCRACIA Corpus → Mnemosyne Viva Site

## Problem Statement

> Estado implementado: `scripts/corpus_sync.py` realiza validação, filtro,
> transformação e emissão. O export consumido é `corpus/corpus-data.json` do
> repositório `anavvanzin/iconocracy-corpus`; neste repositório, uma cópia local
> pode ser usada para builds reproduzíveis.

Transform academic iconography corpus records (English, research-oriented) into
static site JSON (Portuguese, display-oriented) with strict validation as the
first gate. The pipeline must filter by `editorialStatus === "published"`, remap
fields from English to Portuguese, and produce 3 output files.

---

## 1. Interface Signature

### 1.1 Source Schema (Corpus — Input Gate)

```typescript
// Validated FIRST via JSON Schema. Transformation never touches unvalidated data.

interface CorpusItem {
  id: string;                    // e.g. "FR-1792-01"
  slug?: string;
  title: string;
  dateText: string;              // freeform: "1792", "c. 1830", "1908-1912"
  dateStart?: string | null;
  dateEnd?: string | null;
  country: string;               // native: "França", "Brazil", "França (held in Austria)"
  city?: string;
  author: string;
  collection?: string;
  sourceInstitution: string;
  shortDescription?: string;
  longDescription?: string;
  symbols?: string[];
  tags: string[];
  concepts?: string[];
  bibliography?: any[];
  rights?: string;
  license?: string;
  credit?: string;
  files: Array<{
    type: string;                // "image", "ocr", etc.
    role: string;                // "primary", "secondary"
    path: string;                // "/assets/corpus/fr-moitte-liberte-1792.jpg"
    alt?: string;
  }>;
  derivatives?: any[];
  ocrText?: string;
  language?: string;
  curatorialNotes?: string;
  editorialStatus: "draft" | "review" | "published" | "archived";
  provenance?: string;
  externalIdentifiers?: any[];
  iiifManifest?: string;
  seo?: { title?: string; description?: string };
  countryCode?: string;
  year?: number;
  regime: string;                // "FUNDACIONAL", "NORMATIVO", "MILITAR", "CONTRA-alegoria"
  support?: string;              // "gravura", "fotografia", "pintura"
  order?: number;
}
```

### 1.2 Target Schema (Site — Output Shape)

```typescript
// Generated AFTER validation. No schema drift possible.

interface AcervoItem {
  id: string;                    // passthrough
  titulo: string;                // ← title
  pais: string;                  // ← country (normalized to PT)
  data: string;                  // ← dateText
  autoria: string;               // ← author
  instituicao: string;           // ← sourceInstitution
  regime: string;                // ← regime (normalized to PT title case)
  motivos: string[];             // ← tags (filtered: country codes + regime labels stripped)
  imagem: string;                // ← files[0].path (primary image, or "")
  tem_imagem: boolean;           // ← derived: files has primary image?
  desc: string;                  // ← shortDescription (truncated to 600 chars)
  longDesc: string;              // ← longDescription
  notasCuratoriais: string;      // ← curatorialNotes
  iconographic_metadata?: object; // passthrough (when present)
}
```

### 1.3 Stats Output Shape

```typescript
interface StatsOutput {
  total: number;                 // count of published items
  paises: number;                // distinct country count
  com_imagem: number;            // items with tem_imagem === true
  periodo: { min: number | null; max: number | null };
  por_pais: Array<{ pais: string; n: number }>;
  por_regime: Array<{ regime: string; chave: string; n: number }>;
  motivos: Array<{ motivo: string; n: number }>;
}
```

### 1.4 Pipeline Method

```typescript
/**
 * Core pipeline: validate → filter → transform → emit.
 * 
 * @param source   - Raw corpus JSON array (from corpus.json)
 * @param schema   - JSON Schema object for input validation
 * @param opts     - Pipeline configuration
 * @returns        - EmitResult with paths to generated files
 * @throws         - ValidationError if source fails schema gate
 */
function syncCorpusToSite(
  source: CorpusItem[],
  schema: JsonSchema,
  opts?: {
    statusFilter?: string;       // default: "published"
    outputDir?: string;          // default: "site/data/"
    strict?: boolean;            // default: true (reject unknown fields)
  }
): EmitResult;

interface EmitResult {
  acervo: AcervoItem[];          // transformed items
  stats: StatsOutput;            // aggregated statistics
  regimes: RegimeSummary[];      // regime breakdown
  meta: {
    sourceCount: number;         // total items in source
    publishedCount: number;      // items after status filter
    emittedCount: number;        // items in output
    validationMode: "jsonschema" | "minimal";
    errors: string[];            // empty on success
  };
}
```

### 1.5 Field Mapping Table (Single Source of Truth)

```
┌─────────────────────────┬──────────────────────┬──────────────────────────────────┐
│ Corpus Field            │ Site Field           │ Transform                        │
├─────────────────────────┼──────────────────────┼──────────────────────────────────┤
│ id                      │ id                   │ passthrough                      │
│ title                   │ titulo               │ passthrough                      │
│ country                 │ pais                 │ norm_country() → PT              │
│ dateText                │ data                 │ passthrough                      │
│ author                  │ autoria              │ passthrough                      │
│ sourceInstitution       │ instituicao           │ passthrough                      │
│ regime                  │ regime               │ REGIME_PT map → title case       │
│ tags                    │ motivos              │ strip country codes, regime tags │
│ files[role=primary].path│ imagem               │ first primary image path or ""   │
│ (derived)               │ tem_imagem           │ bool( imagem )                   │
│ shortDescription        │ desc                 │ [:600] truncation                │
│ longDescription         │ longDesc             │ passthrough                      │
│ curatorialNotes         │ notasCuratoriais     │ passthrough                      │
│ editorialStatus         │ (filter gate)        │ must === "published"             │
└─────────────────────────┴──────────────────────┴──────────────────────────────────┘
```

---

## 2. Usage Examples

### 2.1 Minimal — One-shot sync

```python
from corpus_sync import sync_corpus_to_site

result = sync_corpus_to_site(
    source=json.loads(Path("corpus.json").read_text()),
    schema=json.loads(Path("schemas/corpus.schema.json").read_text()),
)
# result.acervo  → list of AcervoItem dicts
# result.stats   → StatsOutput dict
# result.meta    → { sourceCount: 30, publishedCount: 0, emittedCount: 0, ... }
```

### 2.2 CLI — With filter override

```bash
# Default: filter by published
python scripts/corpus_sync.py --corpus data/corpus.json --out site/data/

# Draft mode (for development)
python scripts/corpus_sync.py --corpus data/corpus.json --status draft --out site/data/
```

### 2.3 Programmatic — Custom transform hooks

```python
result = sync_corpus_to_site(
    source=corpus,
    schema=schema,
    opts={"strict": True, "statusFilter": "published"},
)

# Inspect validation quality
if result.meta.errors:
    print(f"Schema violations: {len(result.meta.errors)}")
    for e in result.meta.errors:
        print(f"  {e}")

# Write outputs
write_json(output_dir / "acervo.json", result.acervo)
write_json(output_dir / "stats.json", result.stats)
write_json(output_dir / "regimes.json", result.regimes)
```

### 2.4 Single Item Transform (unit testing)

```python
from corpus_sync import transform_item

item = transform_item(corpus_record)
assert item["titulo"] == "Liberté"
assert item["pais"] == "França"
assert item["regime"] == "Fundacional"
assert item["tem_imagem"] is True
assert item["imagem"] == "/assets/corpus/fr-moitte-liberte-1792.jpg"
```

---

## 3. What This Design Hides

| Hidden Concern | How It's Hidden | Why |
|---|---|---|
| **Image resolution** (HTTP URLs vs local paths vs IIIF) | `imagem` is always a string path; resolution happens at site build time | Corpus uses `/assets/corpus/...` relative paths. The site's asset pipeline or CDN resolves these. Keeping paths raw means the same data works local + deployed. |
| **Country normalization logic** (English → Portuguese, edge cases) | Encapsulated in `norm_country()` with a fixed lookup table | The corpus has "France", "Brazil", "France (held in Austria)", etc. The mapping table is the single source of truth, not scattered if/else chains. |
| **Regime classification semantics** | `REGIME_PT` dictionary maps internal codes to display labels | The academic classification system (FUNDACIONAL, NORMATIVO, etc.) is an internal taxonomy. The site only needs the Portuguese display form. |
| **Motif/tag noise filtering** | `motivos` strips country codes (e.g. "FR"), regime labels, and generic terms | The corpus tags serve dual purposes: editorial metadata (country prefix, regime) and semantic motifs. The site only shows semantic motifs. |
| **Schema evolution across two repos** | Each side has its own JSON Schema; the pipeline translates between them | `anavvanzin/corpus.json` and `mnemosyne-viva/site/data/` evolve independently. The sync pipeline is the contract boundary. |
| **Missing/partial data** | Defaults applied during transform (empty strings, null image, etc.) | Academic records are inherently incomplete. The pipeline never fails on missing optional fields — it degrades gracefully. |
| **Aggregation logic** (stats, regime breakdowns) | Encapsulated in `build_stats()` and `build_regimes()` | Consumers don't need to know how `por_pais` or `motivos` counts are computed. They get pre-computed aggregates. |
| **Sort order** (images first, then by country) | Applied in `build_items()` with a stable sort key | The site's grid display needs a specific visual order. The sort is a build-time decision, not a consumer responsibility. |

---

## 4. Trade-offs

### 4.1 Validation Strictness

| Choice | Pros | Cons |
|---|---|---|
| **Strict (additionalProperties: false)** | Catches schema drift early; no silent data loss | Breaks on every new field added to corpus; requires schema + code updates in lockstep |
| **Lenient (additionalProperties: true)** ← CURRENT | Resilient to corpus evolution; new fields pass through harmlessly | Unknown fields silently ignored in output; schema violations harder to detect |
| **Recommended: Strict input + lenient passthrough** | Validates required fields + types; unknown fields are warnings, not errors | Moderate complexity; needs a "strict mode" toggle |

**Decision:** Use `additionalProperties: true` with a `required` array. The schema gates on structure completeness, not field purity. This matches the existing `validate_acervo.py` approach which uses `Draft7Validator` with strict required checks.

### 4.2 Two-Source vs Single-Source Architecture

The current system has **two** JSON files feeding the pipeline:
- `corpus-data.json` (full corpus, for stats)
- `corpus-data-enriched.json` (curated subset, for display)

**Trade-off:**
- ✅ Two sources allow partial curation (only enriched items appear in acervo)
- ❌ Two sources create sync drift risk (stats counted from full corpus, display from subset)
- **This design proposes:** A single `corpus.json` source with `editorialStatus` as the gate. The filter replaces the two-file split. One source of truth.

### 4.3 Output Granularity

| Option | Trade-off |
|---|---|
| **Single `acervo.json`** | Simple; site reads one file. But stats require re-parsing. |
| **`acervo.json` + `stats.json`** ← CURRENT | Pre-computed aggregates avoid client-side computation. Stats stay in sync with source. |
| **`acervo.json` + `stats.json` + `regimes.json`** ← PROPOSED | Third file adds explicit regime breakdown (already in stats, but makes it first-class for filtering UI). |

### 4.4 Transformation Language

| Option | Trade-off |
|---|---|
| **Python (current)** | No build step; `jsonschema` for validation; direct JSON manipulation. Easy to test. |
| **TypeScript** | Type-safe end-to-end; but adds Node.js dependency to academic workflow. |
| **JSONata / jq** | Declarative transforms; but hard to debug complex mappings. |

**Decision:** Python. The existing `build_data.py` is 191 lines, stdlib-only, and works. The schema-first upgrade adds ~80 lines for validation + the mapping table.

### 4.5 What Gets Validated vs Transformed

```
                    ┌─────────────┐
                    │ corpus.json │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  VALIDATE   │ ← JSON Schema gate
                    │  (structure │   - required fields present?
                    │   + types)  │   - id pattern matches?
                    └──────┬──────┘   - strings are strings?
                           │
                    ┌──────▼──────┐
                    │   FILTER    │ ← editorialStatus === "published"
                    │  (content)  │   - not a schema concern
                    └──────┬──────┘   - business rule
                           │
                    ┌──────▼──────┐
                    │ TRANSFORM   │ ← field mapping + normalization
                    │  (shape)    │   - English → Portuguese names
                    │             │   - country normalization
                    └──────┬──────┘   - regime label mapping
                           │
                    ┌──────▼──────┐
                    │   EMIT      │ ← write JSON files
                    │  (output)   │   - acervo.json
                    │             │   - stats.json
                    └─────────────┘   - regimes.json
```

**Key insight:** Validation checks *what the data is*. Filtering checks *what the data means*. Transform changes *how the data looks*. These are three different concerns with three different failure modes, and the schema-first approach correctly separates them.

---

## 5. JSON Schema (Corpus Input)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "https://iconocracia.com/schemas/corpus.schema.json",
  "title": "ICONOCRACIA Corpus — Schema de entrada para sync",
  "description": "Valida o corpus acadêmico (corpus.json) antes da transformação para o site.",
  "type": "array",
  "items": { "$ref": "#/definitions/corpusItem" },
  "definitions": {
    "corpusItem": {
      "type": "object",
      "additionalProperties": true,
      "required": [
        "id", "title", "dateText", "country",
        "editorialStatus", "regime", "files"
      ],
      "properties": {
        "id": {
          "type": "string",
          "pattern": "^[A-Z]{2,}(-[A-Z0-9]+)+$",
          "description": "ID padronizado: prefixo país + segmentos."
        },
        "title": { "type": "string", "minLength": 1 },
        "dateText": { "type": "string", "minLength": 1 },
        "dateStart": { "type": ["string", "null"] },
        "dateEnd": { "type": ["string", "null"] },
        "country": { "type": "string", "minLength": 1 },
        "city": { "type": ["string", "null"] },
        "author": { "type": ["string", "null"] },
        "sourceInstitution": { "type": ["string", "null"] },
        "shortDescription": { "type": ["string", "null"] },
        "longDescription": { "type": ["string", "null"] },
        "tags": { "type": "array", "items": { "type": "string" } },
        "concepts": { "type": "array", "items": { "type": "string" } },
        "curatorialNotes": { "type": ["string", "null"] },
        "editorialStatus": {
          "type": "string",
          "enum": ["draft", "review", "published", "archived"]
        },
        "regime": { "type": "string" },
        "files": {
          "type": "array",
          "items": { "$ref": "#/definitions/fileEntry" }
        }
      }
    },
    "fileEntry": {
      "type": "object",
      "required": ["type", "path"],
      "properties": {
        "type": { "type": "string" },
        "role": { "type": "string", "enum": ["primary", "secondary", "thumbnail"] },
        "path": { "type": "string", "minLength": 1 },
        "alt": { "type": "string" }
      }
    }
  }
}
```

---

## 6. Implementation Notes

### 6.1 Normalization Maps (Single Source of Truth)

```python
COUNTRY_PT = {
    "France": "França", "Brazil": "Brasil",
    "United States": "Estados Unidos", "Germany": "Alemanha",
    "United Kingdom": "Reino Unido", "Italy": "Itália",
    "Portugal": "Portugal", "Belgium": "Bélgica",
    "Netherlands": "Países Baixos", "Spain": "Espanha",
    # ... extend as corpus grows
}

REGIME_PT = {
    "fundacional": "Fundacional", "normativo": "Normativo",
    "militar": "Militar", "contra-alegoria": "Contra-alegoria",
}

# Tags to strip from motivos (country codes, regime labels, generic)
MOTIF_NOISE = {
    "FR", "BR", "DE", "GB", "IT", "PT", "ES", "US", "MX", "AR",
    "FUNDACIONAL", "NORMATIVO", "MILITAR", "CONTRA-ALLEGORIA",
    "fundacional", "normativo", "militar",
}
```

### 6.2 Image Resolution Strategy

```python
def resolve_image(files: list[dict]) -> tuple[str, bool]:
    """Extract primary image path from files array."""
    for f in files:
        if f.get("role") == "primary" and f.get("type") == "image":
            return f["path"], True
    # Fallback: first image-type file
    for f in files:
        if f.get("type") == "image":
            return f["path"], True
    return "", False
```

### 6.3 CI Integration

```yaml
# .github/workflows/sync.yml
- name: Validate corpus schema
  run: python scripts/corpus_sync.py --validate-only --corpus data/corpus.json

- name: Build site data
  run: python scripts/corpus_sync.py --corpus data/corpus.json --out site/data/

- name: Verify outputs
  run: python scripts/validate_acervo.py --json site/data/acervo.json
```

---

## 7. Current State & Gap Analysis

| Aspect | Current | Proposed |
|---|---|---|
| **Sources** | Two JSON files (corpus-data + enriched) | Single `corpus.json` with editorialStatus gate |
| **Schema** | One schema for enriched data only | Schema for input corpus + schema for output acervo |
| **Validation** | `validate_acervo.py` (post-hoc, on enriched) | Pre-transform validation gate |
| **Filter** | Hardcoded two-file split | `editorialStatus` enum filter |
| **Transform** | `build_data.py` (191 lines) | Refactored into validate→filter→transform→emit |
| **Output files** | acervo.json + stats.json | acervo.json + stats.json + regimes.json |

### Immediate blocker

The current upstream public export does not yet contain `editorialStatus`. The
pipeline therefore treats an absent status as `published`; once the upstream
field is introduced, only explicitly published records are emitted. This avoids
an accidental empty public site while preserving the editorial gate.
