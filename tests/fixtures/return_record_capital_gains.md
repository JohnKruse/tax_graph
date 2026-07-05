# Tax Graph Return Record

## Metadata
- Tax year: 2025
- Filing status: single
- Generated date: 2026-07-05
- Tax Graph version: test-version
- Target node: form_1040_2025_line_7_capital_gain_loss

## Facts Ledger
- Proceeds (Box 1d) (`form_1099b_2025_box_1d_proceeds`): 12000
  - Source: document_label=Sample broker 1099-B (fake), extracted_by=manual
  - Confidence: not recorded
- Cost or other basis (Box 1e) (`form_1099b_2025_box_1e_cost_basis`): 10000
  - Source: document_label=Sample broker 1099-B (fake), extracted_by=manual
  - Confidence: not recorded
- Schedule D, line 7 - Net short-term capital gain or (loss) (`schedule_d_2025_line_7_net_st`): 0
  - Source: extracted_by=manual
  - Confidence: not recorded

## Decision Log
### decision_8949_adjustments
- Question: Does this transaction need any adjustment - for example a wash sale, a basis correction, or a nondeductible loss?
- Options presented:
  - none: No adjustments [choice]
  - has_adjustment: Yes - wash sale, basis correction, or other adjustment [unsupported]
  - not_sure: I'm not sure [escalate]
- Chosen: none - No adjustments [choice]
- Rationale: Broker statement shows a simple covered long-term lot with no adjustment code.
- Decided by: test_filer
- Decided date: 2026-07-05
- Citations:
  - cite_8949_adjustment_codes (Instructions for Form 8949, column (f) - codes): "If you need to make an adjustment to the gain or loss, enter the appropriate code(s) in column (f) and the adjustment amount in column (g)."

## Unsupported / Deferred
- No unsupported or deferred items were recorded.

## Computed Outputs
- Form 1040, line 7 - Capital gain or (loss) (`form_1040_2025_line_7_capital_gain_loss`): 2000 [computed] (operation=COPY; rule=copy_currency_value; citations=cite_schedule_d_16_to_1040_7)

## Trace Summary
- Form 1040, line 7 - Capital gain or (loss) (`form_1040_2025_line_7_capital_gain_loss`): 2000 [computed] (operation=COPY; rule=copy_currency_value; citations=cite_schedule_d_16_to_1040_7)
- Proceeds (Box 1d) (`form_1099b_2025_box_1d_proceeds`): 12000 [input]
- Cost or other basis (Box 1e) (`form_1099b_2025_box_1e_cost_basis`): 10000 [input]
- Form 8949 Part II, column (e) - Cost or other basis (`form_8949_2025_partii_cost`): 10000 [computed] (operation=COPY; rule=copy_currency_value)
- Form 8949 Part II, column (h) - Gain or (loss) (`form_8949_2025_partii_gain_loss`): 2000 [computed] (operation=SUBTRACT; rule=subtract_currency; citations=cite_8949_col_h_gain)
- Form 8949 Part II, column (d) - Proceeds (`form_8949_2025_partii_proceeds`): 12000 [computed] (operation=COPY; rule=copy_currency_value)
- Form 8949 Part II, line 2 - Total gain or (loss) (`form_8949_2025_partii_total_gain_loss`): 2000 [computed] (operation=SUM; rule=sum_currency)
- Schedule D, line 15 - Net long-term capital gain or (loss) (`schedule_d_2025_line_15_net_lt`): 2000 [computed] (operation=SUM; rule=sum_currency)
- Schedule D, line 16 - Total capital gain or (loss) (`schedule_d_2025_line_16_total`): 2000 [computed] (operation=SUM; rule=sum_currency)
- Schedule D, line 7 - Net short-term capital gain or (loss) (`schedule_d_2025_line_7_net_st`): 0 [input]
- Schedule D, line 8b - Long-term totals from Form 8949 (gain/loss) (`schedule_d_2025_line_8b_gain`): 2000 [computed] (operation=COPY; rule=copy_currency_value)

## Carryforwards
- No carryforwards emitted.
- Machine payload: see paired carryforward YAML; do not parse this prose.

## Elections
- No consistency elections recorded.
