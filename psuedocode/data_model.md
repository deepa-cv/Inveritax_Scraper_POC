# data_model_pseudocode.md

# Input model (per job)
ParcelInput:
  county: string              # "Brown", "La Crosse", ...
  platform: string            # "GCS", "Ascent", "LandNav"
  parcel_id: string?          # optional
  owner_name: string?         # optional
  address: string?            # optional


# Normalized per-parcel record used inside worker
ParcelTaxRecord:
  # Identity
  county: string
  platform: string
  parcel_id: string?
  owner_name: string?
  address: string?
  tax_year: int

  # Delinquent tax data
  delinquent_status: enum("delinquent", "paid", "unknown")
  delinquent_amount: decimal?
  delinquent_years: list<int>?      # e.g. [2022, 2023]
  delinquent_installments: int?
  penalties_and_interest: decimal?

  # Current-year / escrow data
  current_year_total_tax: decimal?
  installment_1_amount: decimal?
  installment_1_due_date: date?
  installment_2_amount: decimal?
  installment_2_due_date: date?


# Normalizer output tables (DB-ready)

properties table:
  - parcel_id
  - owner_name
  - address
  - county
  - platform

tax_periods table:
  - parcel_id
  - tax_year
  - current_year_total_tax
  - delinquent_status
  - county
  - platform

installments table:
  - parcel_id
  - tax_year
  - installment_number   # 1 or 2
  - amount
  - due_date
  - county

delinquent_taxes table:
  - parcel_id
  - year
  - amount
  - county

penalties_interest table:
  - parcel_id
  - tax_year
  - amount
  - county


# Normalization pseudocode

NORMALIZE(raw_rows):
  init empty lists:
    properties, tax_periods, installments, delinquent_taxes, penalties_interest

  FOR each ParcelTaxRecord r IN raw_rows:
    append property row
    append tax_period row

    IF r.installment_1_amount:
      append installment row #1

    IF r.installment_2_amount:
      append installment row #2

    FOR each y IN r.delinquent_years:
      append delinquent_taxes row for year y

    IF r.penalties_and_interest:
      append penalties_interest row

  RETURN {
    "properties": properties,
    "tax_periods": tax_periods,
    "installments": installments,
    "delinquent_taxes": delinquent_taxes,
    "penalties_interest": penalties_interest,
  }
