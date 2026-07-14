# 🏊‍♂️ Swim Team Scribe Sheet Parser 

This script automates the tedious process of parsing Meet Maestro PDF heat sheets to generate perfectly formatted, ready-to-print Scribe Cards for meet volunteers. 

### ✨ Key Features
* **Dual-Meet Optimized:** Streamlined specifically for Home vs. Away meets. 
* **Smart Placeholders:** Automatically generates "NO SWIMMER" cards for empty lanes.
* **Advanced Relay Parsing:** Intelligently extracts individual swimmer names and swimmer numbers even when nested inside complex relay blocks, including fallback logic for missing team abbreviations.

---

### 📤 Expected Outputs
When you run the parser, it automatically generates the following files directly in your local folder:

* **Master Roster (`.csv`):** A structured spreadsheet containing every swimmer, their assigned event, heat, lane, and team abbreviation. Perfect if you want to use it for mail merging.
* **8.5x11 PDF Mode (Recommended):** Generates standard letter-sized PDFs with four scribe cards per page. It includes dashed cut-lines perfectly centered horizontally and vertically for easy cutting.
* **4x6 PDF Mode:** Generates individual 4x6 inch PDF files for each lane, perfect if you have a dedicated index card printer.

---

### 🛠️ Configuration & Usage
At the bottom of the script, you will find the main execution block. Update these variables before running:

1. **Set the PDF Input:** Place your Meet Maestro Heat Sheet PDF in the project folder and update `INPUT_PDF` with the exact filename.
2. **Define Teams:** Set your `TEAM_ABBREV` (Home) and `OTHER_TEAM_ABBREV` (Away).
3. **League Dictionary:** The script uses `LEAGUE_TEAMS` to map 2-letter codes to full names (e.g., `"SW": "SW Surfers"`). Ensure your opponent is in this dictionary so the regex engine catches all swimmer variations.
4. **Choose Layout:** Set `TEMPLATE_MODE` to `"8.5x11"` or `"4x6"`.
5. **Meters or Yards:** set `POOL_UNITS` to either `METER` or `YARD`. Default should be `YARD`.
6. **Run the Script:** Execute the Python file in your terminal.

---

### 🖨️ Important Printing Instructions
* **Strict Scaling:** Ensure your PDF viewer is set to **"Actual Size" (100%)** when printing the scribe cards.
* **Turn off double-sided printing**: Make sure it doesn't try to print on both sides!
* **Warning:** Do NOT use "Scale to Fit" or "Fit to Page". Doing so will break the strict geometrical sizing required to keep the cards perfectly centered for the cutter.
