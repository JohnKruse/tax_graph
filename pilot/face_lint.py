"""Face-language lint over every DERIVED rule in the drafts.

Reads the PRINTED line face (from outline.yaml, which is what the model saw)
and the operation the pipeline chose, and reports where the two disagree.
A hit is a review flag, never a correction.
"""
import pathlib, re, sys, yaml, collections

ROOT = pathlib.Path(".")
DRAFTS = ROOT / "graph" / "2025" / "_drafts"
RULES = yaml.safe_load(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))


def load(p):
    if not p.exists():
        return []
    v = yaml.safe_load(p.read_text(encoding="utf-8"))
    return v if isinstance(v, list) else []


def faces_by_anchor(outline_path):
    """anchor -> printed face, from the outline the model actually read."""
    out = {}

    def walk(nodes):
        for n in nodes or []:
            if not isinstance(n, dict):
                continue
            a = str(n.get("line_anchor") or "").lower()
            if a and n.get("label"):
                out.setdefault(a, str(n["label"]))
            walk(n.get("children"))

    if not outline_path.exists():
        return out
    doc = yaml.safe_load(outline_path.read_text(encoding="utf-8"))
    walk(doc.get("children") if isinstance(doc, dict) else doc)
    return out


def strip_leading_number(label: str) -> str:
    s = str(label).strip()
    s = re.sub(r"^(Line\s+)?[0-9]+[a-z]?[.)]?\s+", "", s, flags=re.I)
    s = re.sub(r"^[a-z][.)]\s+", "", s).strip()
    return s


hits, checked, unmatched = [], 0, 0
by_doc = collections.Counter()

for d in sorted(DRAFTS.iterdir()):
    if not d.is_dir():
        continue
    faces = faces_by_anchor(d / "outline.yaml")
    rules = {str(r.get("rule_id")): r for r in load(d / "rules.yaml")}
    target_rule = {}
    for e in load(d / "edges.yaml"):
        rid = str(e.get("rule_id") or "")
        if rid in rules:
            target_rule[str(e.get("target"))] = rules[rid]

    for node_id, rule in target_rule.items():
        m = re.search(r"_line_([0-9]+[a-z]?|[a-z])$", node_id, re.I)
        anchor = m.group(1).lower() if m else ""
        face = strip_leading_number(faces.get(anchor, ""))
        op = str(rule.get("operation") or "")
        if not face:
            unmatched += 1
            continue
        checked += 1
        for r in RULES:
            if not re.search(r["face_matches"], face, re.I):
                continue
            bad = ("must_be" in r and op not in r["must_be"]) or (
                "must_not_be" in r and op in r["must_not_be"]
            )
            if bad:
                hits.append((d.name.replace("_2025", ""), anchor, op, r["id"], r["message"], face))
                by_doc[d.name.replace("_2025", "")] += 1

print(f"derived cells with a printed face: {checked}   (no face found: {unmatched})")
print(f"lint hits: {len(hits)}\n")
for doc, anchor, op, rid, msg, face in hits:
    print(f"{doc:14} line {anchor:5} got {op:14} [{rid}]")
    print(f"                 {msg}")
    print(f"                 face: {face[:100]!r}")
print("\nhits by document:", dict(by_doc))
print("rule firing counts:", dict(collections.Counter(h[3] for h in hits)))
