# Autism Caregiving Ebook

Live site:
[https://muszyolo.github.io/autism-caregiving-ebook/](https://muszyolo.github.io/autism-caregiving-ebook/)

This project turns a source-based autism caregiving ebook into a public GitHub Pages website, plus downloadable PDF and EPUB versions.

## What is included

- `docs/index.html`: the live GitHub Pages site
- `docs/autism_caregiving_ebook.pdf`: downloadable PDF
- `docs/autism_caregiving_ebook.epub`: downloadable EPUB
- `scripts/build_ebook.py`: Python builder for PDF, EPUB, and web output
- `output/ebook/autism_caregiving_ebook.md`: manuscript source

## Rebuild locally

```powershell
py -3.13 scripts/build_ebook.py
```

## Notes

- GitHub Pages is configured from the `master` branch using the `docs/` folder.
- A custom domain can be added later by creating a `docs/CNAME` file and pointing DNS to GitHub Pages.
