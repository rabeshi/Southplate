"""Build a reviewable Nigerian food concept registry from CHOWNET-V1 labels."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "ontology"
YOLO = ROOT / "experiments" / "object_detection" / "yolov8"
SOURCE = YOLO / "notes.json"
VERSION = "0.1.0"

# Conservative merges only: orthographic, punctuation, whitespace, and number
# variants. Similar foods and different preparations remain distinct concepts.
OVERRIDES = {
    "Coconot Rice": "Coconut Rice", "Meat  Stir-fry": "Meat Stir-Fry",
    "Noddles": "Noodles", "Noodle": "Noodles", "Others": "Other",
    "Pepped Boiled Chicken": "Peppered Boiled Chicken",
    "Pepped Boiled Fish": "Peppered Boiled Fish",
    "Pepped Fried Beef": "Peppered Fried Beef",
    "Pepped Fried Chicken": "Peppered Fried Chicken",
    "Pepped Fried Egg": "Peppered Fried Egg",
    "Porridge Beans": "Beans Porridge", "Porrige Beans": "Beans Porridge",
    "Mashed Porridge Yam": "Mashed Yam Porridge", "Prawn": "Prawns",
    "Shrimp": "Shrimps", "Sausage Noodle": "Sausage Noodles",
    "Sausage Shrimps Veggie Stir-fry": "Sausage Shrimps Veggie Stir-Fry",
    "Sausage Shrimps Veggie Stir-fry Pasta": "Sausage Shrimps Veggie Stir-Fry Pasta",
    "Sausage Veggie Stir-fry Pasta": "Sausage Veggie Stir-Fry Pasta",
    "Sausage, Shrimps, Veggie Stir-fry": "Sausage Shrimps Veggie Stir-Fry",
    "Sausage, Shrimps, Veggie Stir-fry Pasta": "Sausage Shrimps Veggie Stir-Fry Pasta",
    "Sausage, Veggie Stir-fry Pasta": "Sausage Veggie Stir-Fry Pasta",
    "Sliced Fried Plaintain": "Sliced Fried Plantain",
    "White  Swallow": "White Swallow",
}
AMBIGUOUS = {
    "Aganyi Beans", "Aganyi Stew", "Assorted Protein", "Black Swallow",
    "Diced Sliced Plantain", "Garnished Vegetables", "Green Sauce",
    "Grinded Pepper", "Meat", "Mixed Protein Sauce", "Mixed Rice", "Other",
    "Others", "Protein", "Sauce", "Soup", "Stew", "Swallow", "Vegetable",
    "White Swallow", "White  Swallow",
}
LOCAL_DISHES = {
    "Aganyi Beans", "Aganyi Stew", "Amala", "Asun", "Eba", "Egusi Soup",
    "Ewedu", "Gbegiri", "Gbegiri and Ewedu", "Jollof Pasta", "Jollof Rice",
    "Moi-Moi", "Ofada Rice", "Ofada Stew", "Pap", "Pap and Milk",
    "Pounded Yam", "Suya", "Vegetable Egusi Soup", "Wrapped Fufu",
}
SCIENTIFIC = {
    "Cabbage": "Brassica oleracea var. capitata",
    "Cucumber": "Cucumis sativus",
    "Plantain": "Musa spp. (plantain group)",
    "Red Tomato": "Solanum lycopersicum", "Tomato": "Solanum lycopersicum",
    "Yellow Tomato": "Solanum lycopersicum", "Yam": "Dioscorea spp.",
}
PREPARATIONS = {
    "baked": "baked", "boiled": "boiled", "dry": "dried",
    "fried": "fried", "grilled": "grilled", "mashed": "mashed",
    "peppered": "peppered", "roasted": "roasted", "seasoned": "seasoned",
    "stir-fry": "stir-fried", "wrapped": "wrapped",
}


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "unspecified"


def concept_id(name):
    digest = hashlib.sha1(name.casefold().encode()).hexdigest()[:8]
    return f"NGA-CHOW-{slug(name)[:42]}-{digest}"


def normalize(label):
    return OVERRIDES.get(label, re.sub(r"\s+", " ", label).strip())


def classify(name):
    n = name.casefold()
    if n in {"other", "protein", "assorted protein", "meat", "vegetable"}:
        return "generic_class", "insufficiently specified", "unresolved"
    if any(x in n for x in ("soup", "stew", "sauce", "porridge", "jollof", "rice and", "and beans", "and ewedu", "stir-fry", "shawarma")):
        subgroup = ("soup, stew, or sauce" if any(x in n for x in ("soup", "stew", "sauce")) else
                    "porridge" if "porridge" in n else "rice dish" if "rice" in n else
                    "pasta or noodle dish" if any(x in n for x in ("pasta", "noodle", "spaghetti")) else "mixed dish")
        return "composite_dish", "composite dishes", subgroup
    if any(x in n for x in ("swallow", "amala", "eba", "fufu", "pounded yam")):
        return "prepared_food_component", "starchy staples", "swallow"
    if any(x in n for x in ("rice", "bread", "biscuit", "cake", "macaroni", "noodle", "pasta", "spaghetti", "spring roll")):
        kind = "composite_dish" if any(x in n for x in ("cake", "spring roll", "macaroni and")) else "prepared_food_component"
        return kind, "cereals and cereal products", "grain product"
    if any(x in n for x in ("beans", "moi-moi", "gbegiri")):
        return "prepared_food_component", "legumes, nuts, and seeds", "legume product"
    if any(x in n for x in ("yam", "potato", "plantain")):
        return "prepared_food_component", "roots, tubers, and plantains", "starchy plant food"
    if any(x in n for x in ("fish", "prawn", "shrimp", "snail")):
        return "prepared_food_component", "fish and seafood", "aquatic or molluscan food"
    if any(x in n for x in ("beef", "chicken", "turkey", "meat", "cow skin", "sausage", "hot dog", "suya", "asun")):
        return "prepared_food_component", "meat and poultry", "meat or poultry product"
    if "egg" in n:
        return "prepared_food_component", "eggs", "egg product"
    if "milk" in n:
        return ("ingredient" if n == "milk" else "composite_dish"), "milk and dairy", "milk product"
    if any(x in n for x in ("cabbage", "cucumber", "tomato", "salad", "coleslaw", "pepper", "vegetable", "veggie")):
        kind = "ingredient" if n in {"cabbage", "cucumber", "tomato", "red tomato", "yellow tomato", "vegetable"} else "prepared_food_component"
        return kind, "vegetables", "vegetable product"
    if n == "pap":
        return "prepared_food_component", "cereals and cereal products", "maize porridge"
    return "prepared_food_component", "other foods", "unclassified food"


def preparation(name):
    n = name.casefold()
    return sorted({v for k, v in PREPARATIONS.items() if k in n})


def broader(name):
    value = name
    for prefix in ("Baton ", "Boiled ", "Diced ", "Fried ", "Garnished ", "Grilled ", "Peppered ", "Roasted ", "Seasoned ", "Sliced ", "Wrapped "):
        value = value.removeprefix(prefix)
    return value if value != name else ""


def annotation_counts():
    counts, split_counts, errors = Counter(), {"train": 0, "validation": 0}, []
    for split, dirname in (("train", "train"), ("validation", "valid")):
        for path in sorted((YOLO / dirname / "food" / "labels").glob("*.txt")):
            for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if not line.strip():
                    continue
                split_counts[split] += 1
                parts = line.split()
                if len(parts) != 5:
                    errors.append({"file": str(path.relative_to(ROOT)), "line": line_no, "issue": "expected_5_fields"})
                    continue
                try:
                    class_id, coords = int(parts[0]), [float(v) for v in parts[1:]]
                except ValueError:
                    errors.append({"file": str(path.relative_to(ROOT)), "line": line_no, "issue": "non_numeric_value"})
                    continue
                counts[class_id] += 1
                if not 0 <= class_id < 172:
                    errors.append({"file": str(path.relative_to(ROOT)), "line": line_no, "issue": "class_id_out_of_range"})
                if any(v < 0 or v > 1 for v in coords):
                    errors.append({"file": str(path.relative_to(ROOT)), "line": line_no, "issue": "coordinate_out_of_range", "values": coords})
    return counts, split_counts, errors


def write_csv(path, rows):
    fields = list(rows[0]) if rows else []
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader(); writer.writerows(rows)


def build():
    categories = json.loads(SOURCE.read_text(encoding="utf-8-sig"))["categories"]
    counts, split_counts, annotation_errors = annotation_counts()
    mappings, grouped = [], defaultdict(list)
    for item in categories:
        label, preferred, observed = item["name"], normalize(item["name"]), counts[item["id"]]
        relation = "exact_match" if preferred == re.sub(r"\s+", " ", label).strip() else "exact_synonym"
        ambiguous = label in AMBIGUOUS or preferred in AMBIGUOUS
        notes = (["Label is broad, ambiguous, or locally underspecified."] if ambiguous else [])
        if relation == "exact_synonym": notes.append("Normalization merge requires curator confirmation.")
        if not observed: notes.append("Class is configured but absent from current annotations.")
        row = {
            "source_dataset": "CHOWNET-V1", "source_class_id": item["id"], "observed_label": label,
            "concept_id": concept_id(preferred), "preferred_name": preferred,
            "mapping_relation": "unresolved" if ambiguous else relation,
            "annotation_count": observed, "observed_in_annotations": str(bool(observed)).lower(),
            "mapping_confidence": "low" if ambiguous else "medium" if relation == "exact_synonym" else "high",
            "review_status": "machine_proposed",
            "review_priority": "high" if ambiguous and observed else "medium" if ambiguous or relation == "exact_synonym" else "low",
            "review_notes": " ".join(notes),
        }
        mappings.append(row); grouped[preferred].append(row)

    concepts = []
    for preferred, rows in sorted(grouped.items()):
        kind, group, subgroup = classify(preferred)
        observed = sum(r["annotation_count"] for r in rows)
        ambiguous = any(r["mapping_relation"] == "unresolved" for r in rows)
        notes = (["Resolve meaning before food-composition mapping."] if ambiguous else [])
        if preferred in LOCAL_DISHES: notes.append("Confirm Nigerian recipe variants and regional usage.")
        if kind == "composite_dish": notes.append("Represent recipe variability; do not assign one nutrient record by default.")
        concepts.append({
            "concept_id": concept_id(preferred), "preferred_name": preferred, "concept_type": kind,
            "food_group": group, "subgroup": subgroup, "country": "Nigeria", "region": "West Africa",
            "source_labels": " | ".join(r["observed_label"] for r in rows),
            "source_class_ids": " | ".join(str(r["source_class_id"]) for r in rows),
            "annotation_count": observed, "preparation_methods": " | ".join(preparation(preferred)),
            "scientific_name_candidate": SCIENTIFIC.get(preferred, ""),
            "broader_concept_candidate": broader(preferred), "foodon_id": "", "langual_code": "",
            "infoods_code": "", "national_fct_id": "", "external_mapping_evidence": "",
            "review_status": "machine_proposed",
            "review_priority": "high" if ambiguous or (observed and kind in {"generic_class", "composite_dish"}) else "medium" if preferred in LOCAL_DISHES else "low",
            "review_notes": " ".join(notes),
        })

    review = [{"record_type": "concept", **r} for r in concepts if r["review_priority"] != "low"]
    review += [{"record_type": "label_mapping", **r} for r in mappings if r["review_priority"] != "low"]
    review.sort(key=lambda r: ({"high": 0, "medium": 1}.get(r["review_priority"], 2), -int(r["annotation_count"]), r["preferred_name"]))
    # Use a stable union of review fields because concept and mapping rows differ.
    review_fields = ["record_type"] + sorted({k for r in review for k in r if k != "record_type"})
    report = {
        "schema_version": VERSION, "source_category_count": len(categories),
        "source_ids_contiguous": [c["id"] for c in categories] == list(range(len(categories))),
        "normalized_concept_count": len(concepts), "mapping_count": len(mappings),
        "represented_source_classes": len(counts), "unrepresented_source_classes": len(categories) - len(counts),
        "annotation_count": sum(counts.values()), "annotation_count_by_split": split_counts,
        "annotation_errors": annotation_errors,
        "duplicate_concept_ids": [k for k, n in Counter(c["concept_id"] for c in concepts).items() if n > 1],
        "orphan_mapping_concept_ids": sorted({m["concept_id"] for m in mappings} - {c["concept_id"] for c in concepts}),
        "high_priority_review_records": sum(r["review_priority"] == "high" for r in review),
        "medium_priority_review_records": sum(r["review_priority"] == "medium" for r in review),
    }
    schema = {
        "title": "CHOWNET Nigerian Food Concept Registry", "version": VERSION,
        "controlled_values": {"concept_type": ["ingredient", "prepared_food_component", "composite_dish", "generic_class", "condiment"], "review_status": ["machine_proposed", "curator_reviewed", "expert_validated"]},
        "required": ["concept_id", "preferred_name", "concept_type", "food_group", "subgroup", "country", "review_status"],
        "safety": "Hierarchy membership alone must never be used to infer nutrient composition.",
    }
    write_csv(OUT / "food_concepts.csv", concepts)
    write_csv(OUT / "chownet_label_mappings.csv", mappings)
    with (OUT / "review_queue.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=review_fields, extrasaction="ignore"); writer.writeheader(); writer.writerows(review)
    (OUT / "schema.json").write_text(json.dumps(schema, indent=2) + "\n", encoding="utf-8")
    (OUT / "validation_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    document = {
        "metadata": {"title": "CHOWNET Nigerian Food Concept Registry", "schema_version": VERSION,
                     "generated_on": date.today().isoformat(), "source": str(SOURCE.relative_to(ROOT)).replace("\\", "/"),
                     "country_scope": "Nigeria", "status": "machine-proposed pilot requiring human validation",
                     "geographic_note": "Country context does not imply that a food is exclusive to Nigeria."},
        "hierarchy": [{"id": x, "label": x.replace("_", " ").title(), "parent": "food"} for x in ("ingredient", "prepared_food_component", "composite_dish", "generic_class")],
        "concepts": concepts, "label_mappings": mappings, "validation_summary": report,
    }
    (OUT / "food_ontology.json").write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if not report["source_ids_contiguous"] or report["duplicate_concept_ids"] or report["orphan_mapping_concept_ids"]:
        raise SystemExit("Ontology validation failed; inspect validation_report.json")
    print(f"Built {len(concepts)} concepts from {len(mappings)} labels and {sum(counts.values())} annotations.")
    print(f"Review queue: {len(review)} records; annotation issues: {len(annotation_errors)}.")


if __name__ == "__main__":
    build()
