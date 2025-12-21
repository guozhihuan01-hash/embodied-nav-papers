# scripts/fetch_and_update.py
import arxiv
import json
import re
import os
from datetime import datetime, timezone
from pathlib import Path

DATA_FILE = "data/papers.json"
README_FILE = "README.md"

# 关键词：覆盖具身导航主流方向
KEYWORDS = [
    '"embodied navigation"',
    '"vision and language navigation"',
    '"VLN"',
    '"interactive navigation"',
    '"embodied AI" AND navigation',
    '"robot navigation" AND ("embodied" OR "interactive" OR "instruction")',
    '"object navigation"',
    '"social navigation"',
    '"point navigation"',
    '"navigation"',
    '"semantic navigation"',
]

START_DATE = datetime(2024, 1, 1, tzinfo=timezone.utc)

def load_existing():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_papers(papers):
    Path("data").mkdir(exist_ok=True)
    # 按发布时间倒序（最新在前）
    papers.sort(key=lambda x: x["published"], reverse=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(papers, f, indent=2, ensure_ascii=False)

def extract_github_url(text):
    if not text:
        return None
    pattern = r'https?://github\.com/[a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+'
    matches = re.findall(pattern, text)
    return matches[0] if matches else None

def fetch_papers():
    all_papers = []
    seen_ids = set()
    for kw in KEYWORDS:
        print(f"🔍 Searching: {kw}")
        try:
            search = arxiv.Search(
                query=kw,
                max_results=1000,
                sort_by=arxiv.SortCriterion.SubmittedDate,
                sort_order=arxiv.SortOrder.Descending
            )
            for paper in search.results():
                if paper.published < START_DATE:
                    break  # arXiv 按时间倒序，可提前终止
                if paper.entry_id in seen_ids:
                    continue
                seen_ids.add(paper.entry_id)
                github_url = extract_github_url(paper.summary) or extract_github_url(paper.pdf_url)
                all_papers.append({
                    "id": paper.entry_id,
                    "title": paper.title,
                    "authors": [str(a).split()[-1] for a in paper.authors][:3],
                    "summary": paper.summary.replace("\n", " "),
                    "pdf_url": paper.pdf_url,
                    "github_url": github_url,
                    "published": paper.published.isoformat(),
                    "updated": paper.updated.isoformat()
                })
        except Exception as e:
            print(f"⚠️ Error on '{kw}': {e}")
    return all_papers

def generate_readme(papers):
    now = datetime.now().strftime("%Y-%m-%d %H:%M UTC")
    total = len(papers)
    md = f"""# 🤖 Embodied Navigation Papers (2024–Now)

> Auto-updated daily via GitHub Actions.  
> **Total papers: {total}** | Last updated: **{now}**

| Title | Authors | Code | Date |
|-------|---------|------|------|
"""
    # 显示前 800 篇（GitHub 渲染性能考虑，但数据全量保存）
    for p in papers[:800]:
        title_link = f"[{p['title']}]({p['pdf_url']})"
        authors = ", ".join(p["authors"])
        code_badge = f"[![GitHub](https://img.shields.io/badge/GitHub-Code-green?logo=github)]({p['github_url']})" if p["github_url"] else "—"
        pub_date = p["published"][:10]
        md += f"| {title_link} | {authors} | {code_badge} | {pub_date} |\n"
    
    if total > 800:
        md += f"\n> 💡 Showing top 800 recent papers. Full dataset: [`data/papers.json`](data/papers.json)\n"
    
    md += "\n---\n\n*Powered by [arXiv API](https://arxiv.org/help/api) + GitHub Actions.*\n"
    return md

def main():
    print("🔄 Loading existing papers...")
    existing = load_existing()
    existing_ids = {p["id"] for p in existing}

    print("🌐 Fetching papers from arXiv (2024–Now)...")
    new_papers = fetch_papers()

    truly_new = [p for p in new_papers if p["id"] not in existing_ids]
    print(f"🆕 Found {len(truly_new)} new papers.")

    # 合并 + 去重
    merged = {p["id"]: p for p in (existing + new_papers)}.values()
    merged = list(merged)
    
    save_papers(merged)
    print(f"💾 Total saved: {len(merged)} papers.")

    # 生成并写入 README
    readme_content = generate_readme(merged)
    with open(README_FILE, "w", encoding="utf-8") as f:
        f.write(readme_content)
    print("✅ README.md updated successfully!")

if __name__ == "__main__":
    main()
