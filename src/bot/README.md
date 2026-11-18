# Teams Bot Service (Track B — Platform, Teams & Integration)

This directory contains the Python runtime and activity handlers for the **AI Proposal Assistant** Teams bot.

---

## 1. Directory Structure

```text
src/bot/
├── auth/
│   ├── __init__.py        # SSO & Circle mapping package exports (S0-YK-04)
│   ├── circle_mapper.py   # Department-to-Circle mapping & bid filtering
│   ├── circle_mapping.json # Circles, department rules, metrics & sample bids
│   ├── mock_profiles.json # Mock SSO user personas & persona aliases
│   └── sso_service.py     # Mock / Entra ID OBO SSO identity resolution service
├── cards/
│   ├── intake_card.json   # Base Step 2 RFP Intake Adaptive Card schema (S0-YK-05)
│   └── rfp_catalog.py     # Multi-client RFP catalog & dynamic Adaptive Card generator
├── app.py                 # Server entry point, Bot Activity handlers, and card routing
├── tab_api.py             # Teams Tab hosting & S0-YK-04/05 SSO + Intake APIs
├── config.py              # Environment settings loader
├── test_bot.py            # Unit tests for bot handlers and multi-client Adaptive Cards
├── requirements.txt       # Python dependencies (microsoft-teams-apps, azure-identity, etc.)
└── README.md              # Component documentation
```

---

## 2. Key Capabilities
- **Messaging & Greeting:** Built with the Microsoft Teams SDK (`microsoft-teams-apps`).
- **Multi-Client Repository RFP Support:** Connects directly to all 3 synthetic sample documents under `samples/rfp/`:
  1. 🛡 **Harborline Mutual Insurance Company** (`SAMPLE_RFP_01`) &rarr; Financial Services & Insurance
  2. 🏥 **Cedarbrook Health System** (`SAMPLE_RFI_02`) &rarr; Healthcare & Life Sciences
  3. 🛍 **Velora Retail Group plc** (`SAMPLE_RFP_03`) &rarr; Retail & Consumer Goods
- **RFP Intake Hub & Individual Cards:**
  - Type `intake` &rarr; Renders the **Repository RFP Intake Hub** with 3 client buttons.
  - Type `intake 1`, `intake 2`, or `intake 3` (or `intake cedarbrook`, `intake velora`) &rarr; Directly renders that client's Step 2 Intake Card.
  - Every card features client metadata, AI-matched bid team, and interactive buttons: **`Assign bid owner`** and **`Confirm team`**.
- **Interactive Action Handling:** Responds to button clicks with client-specific confirmations.
- **SSO & Circle Isolation (`S0-YK-04`):** Resolves signed-in user identity & Circle (`Mock SSO` or `Entra ID OBO` toggled cleanly via `USE_MOCK_SSO` / `SSO_MODE`), enforcing strict Circle-level bid filtering across both bot commands (`whoami`, `my bids`, `persona`) and Teams Tab endpoints (`/api/sso/me`, `/api/bids`, `/api/intake/*`).
- **Teams Tab Launch (`Debug Teams Tab App (S0-YK-04)`):** Press `F5` on this launch profile in VS Code (or run `python app.py` and open `http://localhost:3978/`) to open the unified **React 18 + Fluent UI v9** Teams Tab combining Circle-isolated bids and interactive Step 2 RFP Intake confirmation.
- **Zero Cloud Blocker:** Fully debuggable locally using the Microsoft 365 Agents Playground simulator (`http://localhost:56150`).

---

## 3. Local Development & Testing

From the repository root:

1. **Activate virtual environment & run unit tests:**
   ```powershell
   .\venv\Scripts\Activate.ps1
   pytest src/bot -v
   ```

2. **Launch in Playground:**
   - In VS Code, go to **Run and Debug** (`Ctrl + Shift + D`).
   - Select **`Debug in Microsoft 365 Agents Playground`**.
   - Press **`F5`**.
   - In the Playground chat:
     - Type **`intake`** to view the **RFP Intake Hub** and click any of the 3 client buttons.
     - Or type **`intake 1`**, **`intake 2`**, or **`intake 3`** to jump directly to a specific client.
     - Click **`Confirm team`** or **`Assign bid owner`** to verify interactive button responses.
