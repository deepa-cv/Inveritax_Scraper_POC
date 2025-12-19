# county_config_pseudocode.md

# Example: config/brown.yaml

county_name: "Brown"
platform: "GCS"

search:
  # Where to send the search request
  url: "https://prod-landrecords.browncountywi.gov/Search.aspx"
  method: "POST"

  # Which logical inputs this county supports
  supports: ["parcel_id", "owner_name", "address"]

  # Order to try when multiple inputs are present
  preferred_order: ["parcel_id", "address", "owner_name"]

  # Logical input -> actual HTML field name
  fields:
    parcel_id: "ctl00$ContentPlaceHolder1$txtParcel"
    owner_name: "ctl00$ContentPlaceHolder1$txtOwner"
    address: "ctl00$ContentPlaceHolder1$txtAddress"

  submit_button: "ctl00$ContentPlaceHolder1$btnSearch"

parsing:
  # Current year / escrow amounts
  current_year_total_tax:
    strategy: "label_sibling"
    label_contains: "Total Tax"

  installment_1_amount:
    strategy: "label_sibling"
    label_contains: "1st Half Amount"

  installment_1_due_date:
    strategy: "label_sibling"
    label_contains: "1st Half Due"

  installment_2_amount:
    strategy: "label_sibling"
    label_contains: "2nd Half Amount"

  installment_2_due_date:
    strategy: "label_sibling"
    label_contains: "2nd Half Due"

  # Delinquent info
  delinquent_amount:
    strategy: "label_sibling"
    label_contains: "Delinquent Balance"

  delinquent_years:
    strategy: "table_rows"
    table_id: "grdDelinquent"
    year_column: 0
    amount_column: 2
