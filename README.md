# The Autonomous Gatekeeper | UE Asset Validator
### 🛠️ Data Integrity at the Source

## 📑 THE PROBLEM
In large-scale productions, technical debt grows exponentially when assets enter the engine with naming inconsistencies, missing collisions, or unoptimized LODs. Manual auditing is slow, prone to error, and expensive.

## 🚀 THE SOLUTION
A Python-based validation engine for Unreal Engine 5 that audits 3D assets during the ingestion process. It ensures every asset follows the studio's technical standards before it can be used in production.

## 🛠️ CORE FEATURES (Roadmap)
- [ ] **Naming Convention Audit:** Automatic prefix verification (`SM_`, `T_`, `M_`).
- [ ] **Geometry Validation:** Detection of high poly counts and missing UV channels.
- [ ] **Automated Logging:** Generation of success/failure reports for the Pipeline Observatory.

## 💻 INSTALLATION & USAGE
1. Clone this repository into your `Content/Python` folder.
2. Enable the **Python Editor Script Plugin** in Unreal Engine.
3. Run the main validator script via the Unreal Console or VS Code.

## 📊 PIPELINE INTEGRATION
This tool is the first pillar of my **Engineering Manifesto**, focused on **Data Integrity** and **Automation First**.
