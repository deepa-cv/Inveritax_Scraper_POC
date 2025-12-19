# tests_pseudocode.md

# 1. Smoke tests – end-to-end per county

FOR each county IN ALL_COUNTIES:
  FOR each test_parcel IN TEST_PARCELS[county]:
    record = SCRAPE_AND_NORMALIZE(county, test_parcel)

    # Basic sanity
    ASSERT record is not null
    ASSERT record.tax_year is not null

    # Amount sanity
    IF record.current_year_total_tax is not null:
      ASSERT record.current_year_total_tax >= 0

    IF both installments present:
      total_inst = record.installment_1_amount + record.installment_2_amount
      ASSERT approx_equal(total_inst, record.current_year_total_tax, tolerance=0.05)


# 2. Selector / label health checks – config vs live HTML

FOR each cfg IN LOAD_ALL_CONFIGS():
  html = FETCH_SEARCH_PAGE(cfg.search.url)
  soup = BeautifulSoup(html, "lxml")

  FOR each (field, rule) IN cfg.parsing:
    IF rule.strategy == "label_sibling":
      label = FIND_CELL_CONTAINING_TEXT(soup, rule.label_contains)
      ASSERT label is not None, f"{cfg.county} missing label for {field}"

    IF rule.strategy == "table_rows":
      table = soup.find(id=rule.table_id)
      ASSERT table is not None, f"{cfg.county} missing table {rule.table_id}"
      ASSERT table has > 1 data row


# 3. HTML snapshot diff (optional early-warning)

FOR each county IN ALL_COUNTIES:
  current_html = SCRAPE_HTML_FOR_TEST_PARCEL(county)
  baseline_html = LOAD_BASELINE_HTML(county)

  diff_score = HTML_DIFF(current_html, baseline_html)  # 0..1

  ASSERT diff_score < 0.2, f"{county} layout changed significantly – investigate"


# 4. Validation tests on normalized tables

normalized = RUN_FULL_PIPELINE_ON_SAMPLE()

FOR each row IN normalized.tax_periods:
  IF row.current_year_total_tax is not null:
    ASSERT row.current_year_total_tax >= 0

FOR each parcel_id GROUP in normalized.installments:
  total_inst = SUM(group.amount)
  matching_tax_rows = FILTER(normalized.tax_periods, parcel_id)
  IF any matching_tax_rows:
    tax_total = first(matching_tax_rows).current_year_total_tax
    ASSERT approx_equal(total_inst, tax_total, tolerance=0.05)
