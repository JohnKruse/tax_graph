# M20-S1 extraction measurement snapshot

Ground truth: PyMuPDF page.get_text().
Metric: lowercase word-multiset intersection and difference using token pattern `(?:\$[0-9][0-9,]*(?:\.[0-9]+)?|[a-z0-9%]+)`.

- Form PDFs measured: 16
- Mean shipped-text retention: 100.0% (expected 52.2%; reproduced: false)

## Form corpus

| document | retention | fabrication | producer | pages | widgets | tables |
| --- | ---: | ---: | --- | ---: | ---: | ---: |
| form_1040_2025 | 100.0% | 0.0% | Designer 6.5 | 2 | 199 | 7 |
| form_1099_div_2025 | 100.0% | 0.0% | Designer 6.5 | 6 | 140 | 4 |
| form_1099_int_2025 | 100.0% | 0.0% | Designer 6.5 | 7 | 127 | 4 |
| form_1099b_2025 | 100.0% | 0.0% | Designer 6.5 | 7 | 163 | 4 |
| form_13614_c_2025 | 100.0% | 0.0% | Designer 6.5 | 6 | 297 | 9 |
| form_2441_2025 | 100.0% | 0.0% | Designer 6.5 | 2 | 72 | 8 |
| form_6251_2025 | 100.0% | 0.0% | Designer 6.5 | 2 | 62 | 3 |
| form_8949_2025 | 100.0% | 0.0% | Designer 6.5 | 2 | 202 | 4 |
| form_w2_2025 | 100.0% | 0.0% | Designer 6.5 | 11 | 272 | 6 |
| schedule_1_2025 | 100.0% | 0.0% | Designer 6.5 | 2 | 73 | 2 |
| schedule_1a_2025 | 100.0% | 0.0% | Designer 6.5 | 2 | 54 | 5 |
| schedule_2_2025 | 100.0% | 0.0% | Designer 6.5 | 2 | 63 | 3 |
| schedule_3_2025 | 100.0% | 0.0% | Designer 6.5 | 1 | 37 | 1 |
| schedule_a_2025 | 100.0% | 0.0% | Designer 6.5 | 1 | 33 | 1 |
| schedule_b_2025 | 100.0% | 0.0% | Designer 6.5 | 1 | 72 | 2 |
| schedule_d_2025 | 100.0% | 0.0% | Designer 6.5 | 2 | 55 | 4 |

## Headline reproduction

- form_13614_c_2025: measured 100.0%, expected 17.0%, reproduced: false
- form_1040_2025: measured 100.0%, expected 52.0%, reproduced: false
- schedule_3_2025: measured 100.0%, expected 85.7%, reproduced: false

## Producer-robustness corpus

The corpus is test data only. It is not in the acquisition manifest and does not enter graph data.

| document | producer | text | widgets | structure |
| --- | --- | --- | --- | --- |
| california_form_540_2024 | Adobe PDF Library 15.0 | present (2017 words) | present (180) | present (3) |
| irs_form_1040_1999 | APJavaScript 2.2.1 Windows SPDF_1112 Oct  3 2005 | present (1491 words) | present (265) | present (9) |
