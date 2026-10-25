import os, json, time
from agent import analyze_file, to_markdown, _good

IMG_DIR, OUT_DIR = "images", "outputs"
os.makedirs(OUT_DIR, exist_ok=True)
exts = (".jpg", ".jpeg", ".png", ".webp")
all_md = ["# UC04 Visual Investigation Reports\n"]
summary = []

for name in sorted(os.listdir(IMG_DIR)):
    if not name.lower().endswith(exts):
            if os.path.exists(os.path.join(OUT_DIR, name + ".json")):
                print("Skipping (already done):", name)
                continue
        continue
    print("Analyzing", name)
    try:
        report, _ = analyze_file(os.path.join(IMG_DIR, name), use_search=False)
    except Exception as e:
        print("  failed:", str(e)[:150])
        continue
    if not report.get("primary_subject"):
        print("  WARNING: empty report for", name)
    with open(os.path.join(OUT_DIR, name + ".json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    all_md.append(f"\n---\n## {name}\n" + to_markdown(report))
    conf = report.get("location_confidence") or {}
    summary.append(f"| {name} | {report.get('identified_landmark','?')} | {conf.get('level','?')} |")
    time.sleep(5)

all_md.append("\n---\n## Summary table\n| Image | Landmark | Confidence |\n|---|---|---|\n" + "\n".join(summary))
all_md.append(f"\n*Model used: {_good['model']}*")
with open(os.path.join(OUT_DIR, "all_reports.md"), "w", encoding="utf-8") as f:
    f.write("\n".join(all_md))
print("Done. See outputs/all_reports.md")