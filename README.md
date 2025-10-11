# Mano Vendor Onboarding Calculator

This Streamlit app models the vendor onboarding workflow so procurement teams can play out different duration assumptions and understand how the full process shifts. The UI ships with Mano-branded styling and is completely self-contained in this repository.

## Deployment

The vendor onboarding calculator is designed to live alongside the existing RFS calculator but should be deployed as its **own** Streamlit app so that each tool has a distinct URL. On Streamlit Community Cloud:

1. Click **“New app”** and point it at this repository.
2. Set the “Main file path” to `vendor_onboarding_calculator.py`.
3. Give the app a unique subdomain (for example, `vendor-onboarding-calculator.streamlit.app`).

By creating a brand-new app entry instead of reusing the existing RFS calculator deployment, Streamlit will provision a separate URL and keep the two tools isolated.

## Quick Start (Local)

```bash
# 1) Install deps
pip install -r requirements.txt    # or: py -m pip install -r requirements.txt

# 2) Run
streamlit run vendor_onboarding_calculator.py
# If PATH issues: py -m streamlit run vendor_onboarding_calculator.py
