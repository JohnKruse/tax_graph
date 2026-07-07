# Tax Graph Return Record

## Metadata
- Tax year: 2025
- Filing status: single
- Generated date: 2026-07-05
- Tax Graph version: test-version
- Target node: form_1040_2025_line_7_capital_gain_loss

## Facts Ledger
- Schedule D, line 7 - Net short-term capital gain or (loss) (`schedule_d_2025_line_7_net_st`): 0
  - Source: extracted_by=manual
  - Confidence: not recorded
- Form 8949 Part II, line 1, column (d) - Proceeds (`form_8949_2025_part_ii_line_1_column_d#lot_1`): 12000
  - Source: document_label=Sample broker 1099-B (fake), extracted_by=manual
  - Confidence: not recorded
- Form 8949 Part II, line 1, column (e) - Cost or other basis (`form_8949_2025_part_ii_line_1_column_e#lot_1`): 10000
  - Source: document_label=Sample broker 1099-B (fake), extracted_by=manual
  - Confidence: not recorded
- Form 8949 Part II, line 1, column (g) - Adjustment amount (`form_8949_2025_part_ii_line_1_column_g#lot_1`): 0
  - Source: document_label=Sample broker 1099-B (fake), extracted_by=manual
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
- Form 8949 Part I, line 1, column (d) - Proceeds (`form_8949_2025_part_i_line_1_column_d`): blank [table_template]
- Form 8949 Part I, line 1, column (d) minus column (e) (`form_8949_2025_part_i_line_1_column_d_minus_e`): blank [table_template]
- Form 8949 Part I, line 1, column (e) - Cost or other basis (`form_8949_2025_part_i_line_1_column_e`): blank [table_template]
- Form 8949 Part I, line 1, column (g) - Adjustment amount (`form_8949_2025_part_i_line_1_column_g`): blank [table_template]
- Form 8949 Part I, line 1, column (h) - Gain or (loss) (`form_8949_2025_part_i_line_1_column_h`): blank [table_template]
- Form 8949 Part I, line 2, column (d) total (`form_8949_2025_part_i_line_2_line_2_column_d_total`): 0 [table_total] (operation=SUM; citations=cite_8949_col_h_gain,cite_8949_line2_totals)
- Form 8949 Part I, line 2, column (e) total (`form_8949_2025_part_i_line_2_line_2_column_e_total`): 0 [table_total] (operation=SUM; citations=cite_8949_col_h_gain,cite_8949_line2_totals)
- Form 8949 Part I, line 2, column (g) total (`form_8949_2025_part_i_line_2_line_2_column_g_total`): 0 [table_total] (operation=SUM; citations=cite_8949_col_h_gain,cite_8949_line2_totals)
- Form 8949 Part I, line 2, column (h) total (`form_8949_2025_part_i_line_2_line_2_column_h_total`): 0 [table_total] (operation=SUM; citations=cite_8949_col_h_gain,cite_8949_line2_totals)
- Form 8949 Part II, line 1, column (d) - Proceeds (`form_8949_2025_part_ii_line_1_column_d`): blank [table_template]
- Form 8949 Part II, line 1, column (d) - Proceeds#lot_1 (`form_8949_2025_part_ii_line_1_column_d#lot_1`): 12000 [table_input]
- Form 8949 Part II, line 1, column (d) minus column (e) (`form_8949_2025_part_ii_line_1_column_d_minus_e`): blank [table_template]
- Form 8949 Part II, line 1, column (d) minus column (e)#lot_1 (`form_8949_2025_part_ii_line_1_column_d_minus_e#lot_1`): 2000 [table_computed] (operation=SUBTRACT; rule=subtract_currency; citations=cite_8949_col_h_gain)
- Form 8949 Part II, line 1, column (e) - Cost or other basis (`form_8949_2025_part_ii_line_1_column_e`): blank [table_template]
- Form 8949 Part II, line 1, column (e) - Cost or other basis#lot_1 (`form_8949_2025_part_ii_line_1_column_e#lot_1`): 10000 [table_input]
- Form 8949 Part II, line 1, column (g) - Adjustment amount (`form_8949_2025_part_ii_line_1_column_g`): blank [table_template]
- Form 8949 Part II, line 1, column (g) - Adjustment amount#lot_1 (`form_8949_2025_part_ii_line_1_column_g#lot_1`): 0 [table_input]
- Form 8949 Part II, line 1, column (h) - Gain or (loss) (`form_8949_2025_part_ii_line_1_column_h`): blank [table_template]
- Form 8949 Part II, line 1, column (h) - Gain or (loss)#lot_1 (`form_8949_2025_part_ii_line_1_column_h#lot_1`): 2000 [table_computed] (operation=SUM; rule=sum_currency; citations=cite_8949_col_h_gain)
- Form 8949 Part II, line 2, column (d) total (`form_8949_2025_part_ii_line_2_line_2_column_d_total`): 12000 [table_total] (operation=SUM; rule=sum_currency; citations=cite_8949_col_h_gain,cite_8949_line2_totals)
- Form 8949 Part II, line 2, column (e) total (`form_8949_2025_part_ii_line_2_line_2_column_e_total`): 10000 [table_total] (operation=SUM; rule=sum_currency; citations=cite_8949_col_h_gain,cite_8949_line2_totals)
- Form 8949 Part II, line 2, column (g) total (`form_8949_2025_part_ii_line_2_line_2_column_g_total`): 0 [table_total] (operation=SUM; rule=sum_currency; citations=cite_8949_col_h_gain,cite_8949_line2_totals)
- Form 8949 Part II, line 2, column (h) total (`form_8949_2025_part_ii_line_2_line_2_column_h_total`): 2000 [table_total] (operation=SUM; rule=sum_currency; citations=cite_8949_col_h_gain,cite_8949_line2_totals)
- Schedule D capital loss limit, default filing statuses (`schedule_d_2025_capital_loss_limit_default`): 3000 [parameter] (citations=cite_schedule_d_line21_loss_limit)
- Schedule D capital loss limit, married filing separately (`schedule_d_2025_capital_loss_limit_mfs`): 1500 [parameter] (citations=cite_schedule_d_line21_loss_limit)
- Schedule D, line 15 - Net long-term capital gain or (loss) (`schedule_d_2025_line_15_net_lt`): 2000 [computed] (operation=SUM; rule=sum_currency; citations=cite_span_schedule_d_2025_0025)
- Schedule D, line 16 - Total capital gain or (loss) (`schedule_d_2025_line_16_total`): 2000 [computed] (operation=SUM; rule=sum_currency)
- Schedule D, line 20 - Qualified Dividends and Capital Gain Tax Worksheet (`schedule_d_2025_line_20_tax_computation`): MISSING [unresolved] (citations=cite_schedule_d_line20_deferred)
- Schedule D, line 21 - Loss limited for Form 1040 line 7 (`schedule_d_2025_line_21_capital_loss_limited`): 2000 [computed] (operation=MAX; rule=max_currency; citations=cite_schedule_d_line21_loss_limit)
- Schedule D, line 21 - Capital loss limit for filing status (`schedule_d_2025_line_21_loss_limit`): 3000 [computed] (operation=LOOKUP_TABLE; rule=lookup_capital_loss_limit; citations=cite_schedule_d_line21_loss_limit)
- Schedule D, line 21 - Capital loss limit as a negative amount (`schedule_d_2025_line_21_loss_limit_negative`): -3000 [computed] (operation=NEGATE; rule=negate_currency; citations=cite_schedule_d_line21_loss_limit)
- Schedule D, line 7 - Net short-term capital gain or (loss) (`schedule_d_2025_line_7_net_st`): 0 [computed] (operation=SUM; rule=sum_currency; citations=cite_span_schedule_d_2025_0011)
- Schedule D, line 1b, column (h) - Short-term totals from Form 8949 (`schedule_d_2025_part_i_line_1b_column_h`): 0 [computed] (operation=COPY; rule=copy_currency_value; citations=cite_8949_line2_totals)
- Schedule D, line 2, column (h) - Short-term totals from Form 8949 (`schedule_d_2025_part_i_line_2_column_h`): 0 [computed] (operation=COPY; rule=copy_currency_value; citations=cite_8949_line2_totals)
- Schedule D, line 3, column (h) - Short-term totals from Form 8949 (`schedule_d_2025_part_i_line_3_column_h`): 0 [computed] (operation=COPY; rule=copy_currency_value; citations=cite_8949_line2_totals)
- Schedule D, line 10, column (h) - Long-term totals from Form 8949 (`schedule_d_2025_part_ii_line_10_column_h`): 2000 [computed] (operation=COPY; rule=copy_currency_value; citations=cite_8949_line2_totals)
- Schedule D, line 8b, column (h) - Long-term totals from Form 8949 (`schedule_d_2025_part_ii_line_8b_column_h`): 2000 [computed] (operation=COPY; rule=copy_currency_value; citations=cite_8949_line2_totals)
- Schedule D, line 9, column (h) - Long-term totals from Form 8949 (`schedule_d_2025_part_ii_line_9_column_h`): 2000 [computed] (operation=COPY; rule=copy_currency_value; citations=cite_8949_line2_totals)
- Taxpayer filing status (`taxpayer_2025_filing_status`): single [input]

## Carryforwards
- No carryforwards emitted.
- Machine payload: see paired carryforward YAML; do not parse this prose.

## Elections
- No consistency elections recorded.
