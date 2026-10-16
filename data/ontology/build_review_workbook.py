"""Create an approachable Excel review workbook for nutrition experts."""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Protection, Side
from openpyxl.utils import get_column_letter
from openpyxl.workbook.defined_name import DefinedName
from openpyxl.worksheet.datavalidation import DataValidation

ROOT = Path(__file__).resolve().parents[1]
ONTOLOGY = ROOT / "ontology"
YOLO = ROOT / "experiments" / "object_detection" / "yolov8"
OUTPUT = ONTOLOGY / "CHOWNET_Nutritionist_Review.xlsx"
INITIAL_BATCH_SIZE = 30

NAVY = "17365D"
BLUE = "D9EAF7"
PALE_BLUE = "EAF3F8"
YELLOW = "FFF2CC"
GREEN = "E2F0D9"
RED = "FCE4D6"
GREY = "E7E6E6"
WHITE = "FFFFFF"
thin = Side(style="thin", color="B7B7B7")

LISTS = {
    "valid_concept": ["", "Yes", "No", "Unsure", "Duplicate of another concept"],
    "concept_type": ["", "Ingredient", "Prepared food component", "Composite dish", "Condiment or sauce", "Beverage", "Generic class", "Not a food", "Unsure"],
    "food_group": ["", "Cereals and cereal products", "Roots, tubers, and plantains", "Legumes, nuts, and seeds", "Vegetables", "Fruits", "Meat and poultry", "Fish and seafood", "Eggs", "Milk and dairy", "Oils and fats", "Composite dishes", "Beverages", "Other foods", "Insufficiently specified", "Unsure"],
    "yes_no_unsure": ["", "Yes", "No", "Unsure"],
    "fct_suitability": ["", "Yes—direct match", "Yes—with qualification", "No—recipe required", "No—insufficiently specified", "Unsure"],
    "recommended_action": ["", "Accept as proposed", "Rename", "Merge with another concept", "Keep separate but link as related", "Split into multiple concepts", "Create recipe variants", "Exclude from nutrient estimation", "Needs further evidence"],
    "confidence": ["", "High", "Medium", "Low", "Cannot determine"],
    "review_status": ["Not started", "In progress", "Needs discussion", "Completed", "Adjudicated"],
    "mapping_relation": ["", "Exact match", "Close match", "Broader match", "Narrower match", "Recipe-derived", "No suitable match", "Unsure"],
    "source_type": ["", "National food composition table", "FAO/INFOODS", "FoodOn", "LanguaL", "Peer-reviewed publication", "Government source", "Cookbook or recipe source", "Expert consensus", "Other"],
    "synonym_decision": ["", "Accept merge", "Rename merged concept", "Keep separate but related", "Keep separate and unrelated", "Needs discussion"],
}


def read_csv(name):
    with (ONTOLOGY / name).open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def image_index(mappings):
    by_class = {int(row["source_class_id"]): row["concept_id"] for row in mappings}
    images = defaultdict(list)
    for split, folder in (("train", "train"), ("validation", "valid")):
        label_dir = YOLO / folder / "food" / "labels"
        image_dir = YOLO / folder / "food" / "images"
        for label_file in label_dir.glob("*.txt"):
            class_ids = {int(line.split()[0]) for line in label_file.read_text().splitlines() if line.strip()}
            candidates = sorted(image_dir.glob(label_file.stem + ".*"))
            if not candidates:
                continue
            image_path = candidates[0]
            relative = image_path.relative_to(ONTOLOGY).as_posix() if ONTOLOGY in image_path.parents else "../" + image_path.relative_to(ROOT).as_posix()
            for class_id in class_ids:
                if class_id in by_class and len(images[by_class[class_id]]) < 3:
                    images[by_class[class_id]].append((split, relative))
    return images


def title_row(ws, title, subtitle, end_col):
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=end_col)
    ws["A1"] = title
    ws["A1"].font = Font(size=18, bold=True, color=WHITE)
    ws["A1"].fill = PatternFill("solid", fgColor=NAVY)
    ws["A1"].alignment = Alignment(vertical="center")
    ws.row_dimensions[1].height = 30
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=end_col)
    ws["A2"] = subtitle
    ws["A2"].font = Font(italic=True, color="404040")
    ws["A2"].fill = PatternFill("solid", fgColor=PALE_BLUE)
    ws["A2"].alignment = Alignment(wrap_text=True, vertical="center")
    ws.row_dimensions[2].height = 34


def header(ws, row, labels):
    for col, label in enumerate(labels, 1):
        cell = ws.cell(row, col, label)
        cell.font = Font(bold=True, color=WHITE)
        cell.fill = PatternFill("solid", fgColor=NAVY)
        cell.alignment = Alignment(wrap_text=True, vertical="center")
        cell.border = Border(bottom=thin)
    ws.row_dimensions[row].height = 42


def add_validation(ws, column, start_row, end_row, list_name, list_col, count):
    # A workbook-level named range is required for portable cross-sheet Excel
    # data validation; direct references to a hidden sheet are unreliable.
    formula = f"=list_{list_name}"
    dv = DataValidation(type="list", formula1=formula, allow_blank=True)
    dv.error = "Choose a value from the dropdown list."
    dv.errorTitle = "Invalid selection"
    dv.prompt = "Select the most appropriate option."
    dv.promptTitle = "Reviewer entry"
    dv.showErrorMessage = True
    dv.showInputMessage = True
    ws.add_data_validation(dv)
    dv.add(f"{column}{start_row}:{column}{end_row}")


def build_food_review(wb, concepts, images, list_positions):
    ws = wb.create_sheet("Food Review")
    columns = [
        "Initial batch", "Priority", "Concept ID", "Dataset label(s)", "Annotation count",
        "Example image 1", "Example image 2", "Example image 3", "Proposed name",
        "Valid food concept?*", "Nutritionist preferred name*", "Concept type*",
        "Food group*", "Subgroup", "Broader concept", "Nigerian region(s)",
        "Alternative/local names", "Preparation methods", "Main ingredients",
        "Recipe varies materially?*", "Suitable for direct FCT mapping?*",
        "Recommended action*", "Duplicate/related concept ID", "Confidence*",
        "Evidence/source", "Reviewer comments", "Reviewer name", "Review date",
        "Review status*",
    ]
    title_row(ws, "CHOWNET Nutritionist Food Review", "Yellow columns require reviewer input. Start with rows marked ‘Batch 1’. Use image links to inspect the underlying photographs; do not guess when evidence is insufficient.", len(columns))
    header(ws, 4, columns)
    priority_order = {"high": 0, "medium": 1, "low": 2}
    concepts = sorted(concepts, key=lambda r: (priority_order[r["review_priority"]], -int(r["annotation_count"]), r["preferred_name"]))
    for index, concept in enumerate(concepts, 5):
        values = [
            "Batch 1" if index < 5 + INITIAL_BATCH_SIZE else "Later",
            concept["review_priority"].title(), concept["concept_id"], concept["source_labels"],
            int(concept["annotation_count"]), "", "", "", concept["preferred_name"],
            "", "", "", "", "", concept["broader_concept_candidate"], "",
            "", concept["preparation_methods"], "", "", "", "", "", "",
            "", "", "", "", "Not started",
        ]
        for col, value in enumerate(values, 1):
            cell = ws.cell(index, col, value)
            cell.alignment = Alignment(wrap_text=True, vertical="top")
            cell.border = Border(bottom=thin)
            cell.protection = Protection(locked=col not in {10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29})
            if not cell.protection.locked:
                cell.fill = PatternFill("solid", fgColor=YELLOW)
        for offset, link in enumerate(images.get(concept["concept_id"], []), 6):
            ws.cell(index, offset, f"Open {link[0]} image")
            ws.cell(index, offset).hyperlink = link[1]
            ws.cell(index, offset).style = "Hyperlink"
        if values[0] == "Batch 1":
            ws.cell(index, 1).fill = PatternFill("solid", fgColor=GREEN)
        ws.row_dimensions[index].height = 45
    end = 4 + len(concepts)
    validation_columns = {"J": "valid_concept", "L": "concept_type", "M": "food_group", "T": "yes_no_unsure", "U": "fct_suitability", "V": "recommended_action", "X": "confidence", "AC": "review_status"}
    for column, name in validation_columns.items():
        list_col, count = list_positions[name]
        add_validation(ws, column, 5, end, name, list_col, count)
    ws.auto_filter.ref = f"A4:{get_column_letter(len(columns))}{end}"
    ws.freeze_panes = "J5"
    widths = [12, 10, 32, 28, 12, 19, 19, 19, 24, 18, 26, 22, 25, 24, 24, 20, 24, 22, 30, 20, 27, 28, 28, 14, 32, 32, 20, 15, 18]
    for i, width in enumerate(widths, 1): ws.column_dimensions[get_column_letter(i)].width = width
    # Easy visual scanning of completed and discussion rows.
    ws.conditional_formatting.add(f"A5:AC{end}", FormulaRule(formula=["$AC5=\"Completed\""], fill=PatternFill("solid", fgColor=GREEN)))
    ws.conditional_formatting.add(f"A5:AC{end}", FormulaRule(formula=["$AC5=\"Needs discussion\""], fill=PatternFill("solid", fgColor=RED)))
    ws.sheet_view.showGridLines = False
    ws.protection.sheet = True
    ws.protection.password = "chownet"
    ws.protection.autoFilter = False
    ws.protection.sort = False
    return ws


def build_instructions(wb):
    ws = wb.active; ws.title = "Instructions"
    title_row(ws, "Nutritionist Review Guide", "CHOWNET Nigerian Food Concept Registry · Pilot review workbook", 4)
    sections = [
        ("Purpose", "Confirm what each CHOWNET label means and whether it can safely support dietary assessment. The workbook records expert decisions; it does not ask the reviewer to edit technical ontology files."),
        ("Start here", "Open ‘Food Review’, filter Initial batch to ‘Batch 1’, and complete the yellow fields. Review the linked images before deciding. Aim for 2–4 minutes for a straightforward food; mixed dishes may take longer."),
        ("Required fields", "Fields marked * are required: validity, preferred name, concept type, food group, recipe variability, FCT suitability, recommended action, confidence, and review status."),
        ("When uncertain", "Select ‘Unsure’, ‘Cannot determine’, or ‘Needs discussion’. Never infer hidden ingredients or claim regional equivalence from appearance alone."),
        ("Composite dishes", "Record plausible main ingredients, mark material recipe variation, and recommend recipe variants where oil, ingredients, yield, or preparation could materially change nutrient values."),
        ("Synonyms", "Use ‘Synonym Decisions’ for proposed spelling and number merges. Similar foods are not necessarily synonyms; select ‘Keep separate but related’ when appropriate."),
        ("Evidence", "Provide a citation, URL, FCT name/version, recipe source, or documented expert consensus. Nutrient and external ontology mappings should have traceable evidence."),
        ("Completion", "Set Review status to Completed only when required decisions and evidence/comments are sufficient. Use Adjudicated only after disagreements have been resolved."),
        ("Protection", "Blue/grey fields are generated reference data and are locked. Yellow fields are editable. The sheet password is ‘chownet’ if a project administrator needs to change the layout."),
    ]
    row = 4
    for heading, text in sections:
        ws.cell(row, 1, heading).font = Font(bold=True, color=NAVY, size=12)
        ws.cell(row, 2, text).alignment = Alignment(wrap_text=True, vertical="top")
        ws.merge_cells(start_row=row, start_column=2, end_row=row, end_column=4)
        ws.row_dimensions[row].height = max(35, 15 * (len(text) // 95 + 1))
        row += 2
    ws.column_dimensions["A"].width = 22
    for col in "BCD": ws.column_dimensions[col].width = 30
    ws.sheet_view.showGridLines = False


def simple_review_sheet(wb, name, title, subtitle, columns, rows, editable_from=1):
    ws = wb.create_sheet(name); title_row(ws, title, subtitle, len(columns)); header(ws, 4, columns)
    for r_idx, values in enumerate(rows, 5):
        for c_idx, value in enumerate(values, 1):
            cell = ws.cell(r_idx, c_idx, value); cell.alignment = Alignment(wrap_text=True, vertical="top"); cell.border = Border(bottom=thin)
            if c_idx >= editable_from: cell.fill = PatternFill("solid", fgColor=YELLOW)
        ws.row_dimensions[r_idx].height = 36
    ws.auto_filter.ref = f"A4:{get_column_letter(len(columns))}{max(5,4+len(rows))}"
    ws.freeze_panes = f"A5"
    for i in range(1, len(columns)+1): ws.column_dimensions[get_column_letter(i)].width = 24
    ws.sheet_view.showGridLines = False
    return ws


def build():
    concepts, mappings = read_csv("food_concepts.csv"), read_csv("chownet_label_mappings.csv")
    images = image_index(mappings)
    wb = Workbook(); build_instructions(wb)
    lists = wb.create_sheet("Lists")
    positions = {}
    for col, (name, values) in enumerate(LISTS.items(), 1):
        letter = get_column_letter(col)
        lists.cell(1, col, name); positions[name] = (letter, len(values))
        for row, value in enumerate(values, 2): lists.cell(row, col, value)
        wb.defined_names.append(DefinedName(f"list_{name}", attr_text=f"Lists!${letter}$2:${letter}${len(values)+1}"))
    lists.sheet_state = "hidden"
    food_ws = build_food_review(wb, concepts, images, positions)

    synonym_rows = []
    for concept in concepts:
        labels = concept["source_labels"].split(" | ")
        if len(labels) > 1:
            synonym_rows.append([concept["concept_id"], concept["preferred_name"], " | ".join(labels), concept["annotation_count"], "", "", "", "Not started"])
    syn = simple_review_sheet(wb, "Synonym Decisions", "Proposed Synonym Decisions", "Confirm only true spelling, punctuation, whitespace, or number variants. Similar foods should remain separate and may be linked as related.", ["Concept ID", "Proposed preferred name", "Source labels", "Annotation count", "Decision*", "Correct preferred name", "Reviewer rationale/evidence", "Review status*"], synonym_rows, 5)
    add_validation(syn, "E", 5, 4+len(synonym_rows), "synonym_decision", *positions["synonym_decision"])
    add_validation(syn, "H", 5, 4+len(synonym_rows), "review_status", *positions["review_status"])

    recipe_columns = ["Concept ID", "Food name", "Recipe variant ID", "Variant name", "Country/region", "Ingredient", "Ingredient amount", "Unit", "Preparation", "Cooked yield", "Yield unit", "Servings", "Source/citation", "Reviewer", "Review status"]
    recipe_rows = [[""] * 14 + ["Not started"] for _ in range(100)]
    recipes = simple_review_sheet(wb, "Recipe Variants", "Recipe Variant Evidence", "Use multiple rows per recipe—one row per ingredient. Do not invent quantities; record a source and cooked yield where available.", recipe_columns, recipe_rows, 1)
    add_validation(recipes, "O", 5, 104, "review_status", *positions["review_status"])
    mapping_columns = ["Concept ID", "Food name", "Database/vocabulary", "Database version", "Record ID", "Matched record name", "Mapping relation", "Nutrient basis", "Evidence URL/citation", "Confidence", "Reviewer", "Review date", "Review status", "Notes"]
    mapping_rows = [[""] * 12 + ["Not started", ""] for _ in range(100)]
    composition = simple_review_sheet(wb, "Composition Mappings", "Food-Composition and Ontology Mappings", "Every external ID must be evidence-backed. Prefer Nigerian/West African composition data; document any fallback and mapping qualification.", mapping_columns, mapping_rows, 1)
    add_validation(composition, "G", 5, 104, "mapping_relation", *positions["mapping_relation"])
    add_validation(composition, "J", 5, 104, "confidence", *positions["confidence"])
    add_validation(composition, "M", 5, 104, "review_status", *positions["review_status"])

    dashboard = wb.create_sheet("Dashboard", 1)
    title_row(dashboard, "Review Progress Dashboard", "Formula-driven summary of the Food Review sheet. Open the workbook in Excel or compatible software to recalculate.", 4)
    metrics = [
        ("Total concepts", f"=COUNTA('Food Review'!C5:C{4+len(concepts)})"),
        ("Initial batch", f'=COUNTIF(\'Food Review\'!A5:A{4+len(concepts)},"Batch 1")'),
        ("Completed", f'=COUNTIF(\'Food Review\'!AC5:AC{4+len(concepts)},"Completed")'),
        ("Needs discussion", f'=COUNTIF(\'Food Review\'!AC5:AC{4+len(concepts)},"Needs discussion")'),
        ("Not started", f'=COUNTIF(\'Food Review\'!AC5:AC{4+len(concepts)},"Not started")'),
        ("Completion %", f'=COUNTIF(\'Food Review\'!AC5:AC{4+len(concepts)},"Completed")/COUNTA(\'Food Review\'!C5:C{4+len(concepts)})'),
    ]
    header(dashboard, 4, ["Metric", "Value"])
    for row, (label, formula) in enumerate(metrics, 5):
        dashboard.cell(row, 1, label); dashboard.cell(row, 2, formula)
        dashboard.cell(row, 1).font = Font(bold=True); dashboard.cell(row, 1).fill = PatternFill("solid", fgColor=BLUE)
    dashboard["B10"].number_format = "0%"
    dashboard.column_dimensions["A"].width = 28; dashboard.column_dimensions["B"].width = 18
    dashboard.sheet_view.showGridLines = False

    wb.calculation.fullCalcOnLoad = True
    wb.calculation.forceFullCalc = True
    wb.save(OUTPUT)
    # Structural verification after serialization.
    check = load_workbook(OUTPUT, read_only=False, data_only=False)
    required = {"Instructions", "Dashboard", "Food Review", "Synonym Decisions", "Recipe Variants", "Composition Mappings", "Lists"}
    assert required.issubset(check.sheetnames)
    assert check["Food Review"].max_row == len(concepts) + 4
    assert sum(1 for row in check["Food Review"].iter_rows(min_row=5, min_col=6, max_col=8) for c in row if c.hyperlink) > 0
    assert len(check["Food Review"].data_validations.dataValidation) == 8
    check.close()
    print(f"Created {OUTPUT.name} with {len(concepts)} foods, {len(synonym_rows)} synonym groups, and {sum(len(v) for v in images.values())} image links.")


if __name__ == "__main__":
    build()
