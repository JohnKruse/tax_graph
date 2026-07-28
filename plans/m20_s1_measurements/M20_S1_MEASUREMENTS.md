# M20-S1 extraction measurement snapshot

Ground truth: PyMuPDF page.get_text().
Metric: lowercase word-multiset intersection and difference using token pattern `[a-z0-9$%]+`.

- Form PDFs measured: 16
- Mean shipped-text retention: 52.2% (expected 52.2%; reproduced: true)

## Form corpus

| document | retention | fabrication | producer | pages | widgets | tables |
| --- | ---: | ---: | --- | ---: | ---: | ---: |
| form_1040_2025 | 52.0% | 0.8% | Designer 6.5 | 2 | 199 | 7 |
| form_1099_div_2025 | 24.3% | 2.0% | Designer 6.5 | 6 | 140 | 4 |
| form_1099_int_2025 | 31.7% | 2.7% | Designer 6.5 | 7 | 127 | 4 |
| form_1099b_2025 | 26.2% | 2.9% | Designer 6.5 | 7 | 163 | 4 |
| form_13614_c_2025 | 17.0% | 6.7% | Designer 6.5 | 6 | 297 | 9 |
| form_2441_2025 | 55.3% | 2.9% | Designer 6.5 | 2 | 72 | 8 |
| form_6251_2025 | 67.5% | 0.7% | Designer 6.5 | 2 | 62 | 3 |
| form_8949_2025 | 67.4% | 5.1% | Designer 6.5 | 2 | 202 | 4 |
| form_w2_2025 | 32.8% | 4.4% | Designer 6.5 | 11 | 272 | 6 |
| schedule_1_2025 | 80.5% | 1.3% | Designer 6.5 | 2 | 73 | 2 |
| schedule_1a_2025 | 61.6% | 1.7% | Designer 6.5 | 2 | 54 | 5 |
| schedule_2_2025 | 77.9% | 1.1% | Designer 6.5 | 2 | 63 | 3 |
| schedule_3_2025 | 85.7% | 1.2% | Designer 6.5 | 1 | 37 | 1 |
| schedule_a_2025 | 52.9% | 1.8% | Designer 6.5 | 1 | 33 | 1 |
| schedule_b_2025 | 40.8% | 3.1% | Designer 6.5 | 1 | 72 | 2 |
| schedule_d_2025 | 61.1% | 3.7% | Designer 6.5 | 2 | 55 | 4 |

## Headline reproduction

- form_13614_c_2025: measured 17.0%, expected 17.0%, reproduced: true
- form_1040_2025: measured 52.0%, expected 52.0%, reproduced: true
- schedule_3_2025: measured 85.7%, expected 85.7%, reproduced: true

## Producer-robustness corpus

The corpus is test data only. It is not in the acquisition manifest and does not enter graph data.

| document | producer | text | widgets | structure |
| --- | --- | --- | --- | --- |
| california_form_540_2024 | Adobe PDF Library 15.0 | present (2025 words) | present (180) | present (3) |
| irs_form_1040_1999 | APJavaScript 2.2.1 Windows SPDF_1112 Oct  3 2005 | present (1498 words) | present (265) | present (9) |
