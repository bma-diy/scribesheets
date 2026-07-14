import re
import os
import pandas as pd
import pypdf
import unicodedata
from weasyprint import HTML, CSS

# ==========================================
# 📊 FUNCTION 1: PRE-PROCESSING DATA CLEANER
# ==========================================
def clean_spacing_issues(text, TEAM_ABBREV, OTHER_TEAM_ABBREV):
    first_letter_other, remaining_other = OTHER_TEAM_ABBREV[0], OTHER_TEAM_ABBREV[1:]
    first_letter_my, remaining_my = TEAM_ABBREV[0], TEAM_ABBREV[1:]
    
    text = re.sub(rf'\b{first_letter_other}\s+{remaining_other}(\d{{3,4}})\b', rf'{OTHER_TEAM_ABBREV}\1', text)
    text = re.sub(rf'\b{first_letter_my}\s+{remaining_my}(\d{{3,4}})\b', rf'{TEAM_ABBREV}\1', text)
    
    # 🔧 INTERCEPT AND FIX SMASHED RELAY SIGNATURES (e.g., DSW -> D SW, DSC -> D SC)
    for letter in ['A', 'B', 'C', 'D', 'E', 'F']:
        text = text.replace(f" {letter}{TEAM_ABBREV} ", f" {letter} {TEAM_ABBREV} ")
        text = text.replace(f" {letter}{OTHER_TEAM_ABBREV} ", f" {letter} {OTHER_TEAM_ABBREV} ")
        
    return text

# ==========================================
# 📄 FUNCTION 2: NATIVE CROSS-PLATFORM PRINT ENGINE
# 📄 UPDATED PRINT ENGINE (Multi-Template & Inclusive)
# ==========================================
def generate_html_lane_cards(df_output, TEAM_ABBREV, OTHER_TEAM_ABBREV, mode="4x6"):
    import time # Imported inline for the timer logic
    
    print(f"\n🌐 Generating {mode} PDF packets for {OTHER_TEAM_ABBREV} at {TEAM_ABBREV}...")
    all_entries = df_output.copy()
    
    # ---------------------------------------------------------
    # SHARED HTML TEMPLATE GENERATOR
    # ---------------------------------------------------------
    def build_card_html(row):
        is_relay = "RELAY" in str(row.get('Stroke', '')).upper()
        roster_html = ""
        
        # Logic: NO SWIMMER assigned
        if row.get('AthName1') == 'NO SWIMMER':
            roster_html = "<div>NO SWIMMER ASSIGNED</div>"
        else:
            for num in range(1, 5):
                if row.get(f'AthName{num}'):
                    roster_html += f"<div>{row.get(f'AthNum{num}', '')} {row.get(f'AthName{num}', '')}</div>"

        # Logic: Only show Team/Relay if it exists and is not 'None'
        team_text = ""
        team_abr = str(row.get('TeamAbr2', '')).replace('None', '').strip()
        if team_abr:
            relay_part = f" - {row.get('RelayLetter', '')} Relay" if row.get('RelayLetter') else ""
            team_text = f"<div style='font-weight:bold; margin-bottom: 5px;'>{team_abr}{relay_part}</div>"

        return f"""
            <table class="header-table">
                <tr>
                    <td class="side-col">
                        <div class="ev-ht-label">EVENT</div>
                        <div class="ev-ht-value">{row.get('Ev', '')}</div>
                    </td>
                    <td class="mid-col">
                        <div>{row.get('Stroke', '')}</div>
                        <div>{row.get('AgeGroup', '')}</div>
                        <div>Lane {row.get('Lane', '')}</div>
                    </td>
                    <td class="side-col">
                        <div class="ev-ht-label">HEAT</div>
                        <div class="ev-ht-value">{row.get('HT', '')}</div>
                    </td>
                </tr>
            </table>
            
            <div class="roster-box">
                {team_text}
                {roster_html}
            </div>
            
            <div class="footer-section">
                <div class="time-label">&nbsp;&nbsp;&nbsp;Time: _______________</div>
                <br>
                <div class="time-label">&nbsp;&nbsp;&nbsp;Time: _______________</div>
                <br>
                <div class="time-label">&nbsp;&nbsp;&nbsp;Time: _______________</div>
                
                <div class="participation-container">
                    &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Participation/ DQ?<span class="checkbox"></span>
                </div>
                
                <div class="place-box">Place:&nbsp;&nbsp;&nbsp;&nbsp;1&nbsp;&nbsp;&nbsp;&nbsp;2&nbsp;&nbsp;&nbsp;&nbsp;3&nbsp;&nbsp;&nbsp;&nbsp;4&nbsp;&nbsp;&nbsp;&nbsp;5&nbsp;&nbsp;&nbsp;&nbsp;6</div>
                <div class="icon-bottom-right">{row.get('icon', '')}</div>
            </div>
        """

    # ---------------------------------------------------------
    # SHARED CSS SETTINGS
    # ---------------------------------------------------------
    shared_css = """
        body { font-family: 'Helvetica', sans-serif; margin: 0; padding: 0; }
        .header-table { width: 100%; border-collapse: collapse; margin-bottom: 15px; }
        
        .side-col { width: 25%; text-align: center; vertical-align: middle; }
        .mid-col { width: 50%; text-align: center; vertical-align: middle; font-size: 10pt; line-height: 1.2; }
        
        .ev-ht-label { font-size: 10pt; font-weight: normal; }
        .ev-ht-value { font-size: 28pt; font-weight: normal; line-height: 1.0; margin-top: 2px; }
        
        .roster-box { margin: 15px 0; font-size: 12pt; }
        .footer-section { margin-top: auto; }
        .time-label { font-size: 14pt; font-weight: normal; margin: 10px 0; padding-left: 20px; }
        
        .participation-container { margin: 10px 0; font-size: 12pt; padding-left: 20px; }
        .checkbox { width: 15px; height: 15px; border: 1px solid #000; display: inline-block; vertical-align: middle; margin-left: 10px; }
        
        .place-box { border: 1px solid #000; padding: 5px; margin-top: 10px; font-weight: normal; font-size: 12pt; }
        .icon-bottom-right { position: absolute; bottom: 5px; right: 15px; font-size: 18pt; }
    """

    # =========================================================
    # MODE: 4x6 (Individual Lane Files)
    # =========================================================
    if mode == "4x6":
        css_style = """
            @page { 
                size: 4in 6in; 
                margin-top: 0.55in; margin-bottom: 0.55in; 
                margin-left: 0.3in; margin-right: 0.3in; 
            }
            .scribe-card { 
                width: 3.4in; height: 4.9in; 
                border: 1px solid #000; padding: 15px; 
                display: flex; flex-direction: column; 
                box-sizing: border-box; position: relative; 
            }
        """ + shared_css

        for lane_num in sorted(all_entries['Lane'].unique()):
            lane_data = all_entries[all_entries['Lane'] == lane_num]
            html_content = f"<html><head><style>{css_style}</style></head><body>"
            
            for idx, (_, row) in enumerate(lane_data.iterrows()):
                style_break = "page-break-after: always;" if idx < len(lane_data) - 1 else ""
                html_content += f'<div class="scribe-card" style="{style_break}">'
                html_content += build_card_html(row)
                html_content += '</div>'
                
            html_content += "</body></html>"
            output_filename = f"{OTHER_TEAM_ABBREV}_at_{TEAM_ABBREV}_Lane_{lane_num}_{mode}.pdf"
            HTML(string=html_content).write_pdf(output_filename)
            print(f"✅ Generated: {output_filename}")

    # =========================================================
    # MODE: 8.5x11 (4-Lane Quad Sheets)
    # =========================================================
    elif mode == "8.5x11":
        print("\n⏳ WARNING: Generating 8.5x11 PDF packets may take a couple of minutes. Starting timer...")
        start_total_time = time.time()
        
        css_style = """
            @page { size: 8.5in 11in; margin: 0; }
            .page-container { width: 8.5in; height: 11in; position: relative; box-sizing: border-box; }
            
            /* Dotted cut lines perfectly bisecting the page */
            .cut-line-v { position: absolute; left: 4.25in; top: 0; height: 11in; border-left: 1px dashed #000; z-index: 10; }
            .cut-line-h { position: absolute; top: 5.5in; left: 0; width: 8.5in; border-top: 1px dashed #000; z-index: 10; }
            
            .quadrants { display: flex; flex-wrap: wrap; width: 8.5in; height: 11in; align-content: flex-start; }
            .quadrant { width: 4.25in; height: 5.5in; display: flex; align-items: center; justify-content: center; box-sizing: border-box; }
            
            /* Exact 4x6 scribe card format suspended in the center of each quadrant */
            .scribe-card { 
                width: 3.4in; height: 4.9in; 
                border: 1px solid #000; padding: 15px; 
                display: flex; flex-direction: column; 
                box-sizing: border-box; position: relative; 
                background: #fff; z-index: 1;
            }
        """ + shared_css

        # Dynamically determine the actual lanes present in the dataset
        actual_lanes = set(all_entries['Lane'].unique())
        group1_lanes = [l for l in [1, 2, 3, 4] if l in actual_lanes]
        group2_lanes = [l for l in [5, 6, 7, 8] if l in actual_lanes]
        
        lane_groups = []
        if group1_lanes:
            lane_groups.append(("1-4", group1_lanes))
        if group2_lanes:
            lane_groups.append(("5-8", group2_lanes))

        unique_heats = all_entries[['Ev', 'HT']].drop_duplicates()
        
        for group_idx, (group_name, lanes) in enumerate(lane_groups):
            start_pdf_time = time.time()
            html_content = f"<html><head><style>{css_style}</style></head><body>"
            
            for idx, (_, heat) in enumerate(unique_heats.iterrows()):
                ev = heat['Ev']
                ht = heat['HT']
                heat_rows = all_entries[(all_entries['Ev'] == ev) & (all_entries['HT'] == ht)]
                
                if heat_rows.empty:
                    continue
                    
                template_row = heat_rows.iloc[0]
                style_break = "page-break-after: always;" if idx < len(unique_heats) - 1 else ""
                
                html_content += f'<div class="page-container" style="{style_break}">'
                html_content += '<div class="cut-line-v"></div><div class="cut-line-h"></div>'
                html_content += '<div class="quadrants">'
                
                for lane_num in lanes:
                    lane_row = heat_rows[heat_rows['Lane'] == lane_num]
                    
                    if not lane_row.empty:
                        row_data = lane_row.iloc[0]
                    else:
                        row_data = pd.Series({
                            'Ev': template_row['Ev'],
                            'HT': template_row['HT'],
                            'Stroke': template_row.get('Stroke', ''),
                            'AgeGroup': template_row.get('AgeGroup', ''),
                            'Lane': lane_num,
                            'AthName1': 'NO SWIMMER',
                            'icon': template_row.get('icon', '')
                        })
                        
                    html_content += f'<div class="quadrant"><div class="scribe-card">{build_card_html(row_data)}</div></div>'
                    
                html_content += '</div></div>' 
                
            html_content += "</body></html>"
            
            output_filename = f"{OTHER_TEAM_ABBREV}_at_{TEAM_ABBREV}_Lanes_{group_name}_{mode}.pdf"
            HTML(string=html_content).write_pdf(output_filename)
            
            pdf_time = time.time() - start_pdf_time
            print(f"✅ Generated 8.5x11 packet {group_idx + 1}: {output_filename} (Took {pdf_time:.2f} seconds)")
            
        total_time = time.time() - start_total_time
        print(f"🎉 All 8.5x11 PDF generation complete in {total_time:.2f} seconds!")

# ==========================================
# 📥 FUNCTION 3: PARSING PIPELINE MACHINE
# ==========================================
def weekly_swim_parser(TEAM_ABBREV, INPUT_PDF, OTHER_TEAM_ABBREV, NUM_SWIM_LANES, 
                       LEAGUE_TEAMS, OUTPUT_EXCEL, EVENT_REGISTRY, OTHER_TEAM, MY_TEAM):
                       
    print(f"🚀 Launching Roster-Verified Pipeline for: {INPUT_PDF}")
    print(f"🏊 Configured Pool Grid Setup: {NUM_SWIM_LANES} Lanes")
    print(f"🏄‍♂️ Home: {MY_TEAM} ({TEAM_ABBREV}) vs Away: {OTHER_TEAM} ({OTHER_TEAM_ABBREV})")
    
    # Check for mandatory PDF
    if not os.path.exists(INPUT_PDF):
        print(f"❌ Error: {INPUT_PDF} not found!")
        return None

    print("✅ Event Registry dictionary loaded.")

    # Extract text from current Heat Sheet PDF
    reader = pypdf.PdfReader(INPUT_PDF)
    full_text = ""
    for page in reader.pages:
        page_text = page.extract_text() or ""
        normalized_text = unicodedata.normalize('NFKD', page_text).encode('ASCII', 'ignore').decode('utf-8')
        full_text += normalized_text + "\n"

    print(f"✅ Successfully extracted {len(full_text)} characters from PDF.")

    # ==========================================
    # 🔍 FILE COMPATIBILITY & VALIDATION CHECKS
    # ==========================================
    print("\n⏳ Running file compatibility checks...")
    potential_errors = []

    if len(full_text.strip()) == 0:
        potential_errors.append("PDF text is completely empty.")
    if "Meet Maestro" not in full_text:
        potential_errors.append("Missing Meet Maestro signature metadata.")

    found_events = set(re.findall(r'#(\d+)\s', full_text))
    total_event_count = len(found_events)
    if total_event_count != 70:
        missing = sorted(list(set(map(str, range(1, 71))) - found_events))
        potential_errors.append(f"Incorrect event count ({total_event_count}/70). Missing numbers: {missing}")

    for abbrev in [TEAM_ABBREV, OTHER_TEAM_ABBREV]:
        if abbrev not in full_text:
            potential_errors.append(f"Abbreviation '{abbrev}' not found.")

    if potential_errors:
        print("\n⚠️  POTENTIAL COMPATIBILITY ERRORS DETECTED:")
        for err in potential_errors:
            print(f"   - {err}")
    else:
        print("✅ PASS: File layout structures verified perfectly.\n")

    events_text = {}
    matches = list(re.finditer(r'^#(\d+)\s+(.*)', full_text, re.MULTILINE))
    for idx, match in enumerate(matches):
        ev_num = int(match.group(1))
        start_pos = match.start()
        end_pos = matches[idx+1].start() if idx + 1 < len(matches) else len(full_text)
        events_text[ev_num] = full_text[start_pos:end_pos]

    parsed_rows = []

    for ev_num in sorted(events_text.keys()):
        if ev_num not in EVENT_REGISTRY:
            continue
            
        age_group = EVENT_REGISTRY[ev_num]['AgeGroup']
        stroke = EVENT_REGISTRY[ev_num]['Stroke']
        is_relay = 'RELAY' in stroke.upper()
        text_chunk = events_text[ev_num]
        
        heats_data = re.split(r'Heat\s+(\d+)\s+of\s+(\d+)', text_chunk)
        if len(heats_data) < 2:
            continue
            
        i = 1
        while i < len(heats_data):
            heat_num = int(heats_data[i])
            heat_content = heats_data[i+2]
            i += 3
            
            heat_content_cleaned = clean_spacing_issues(heat_content, TEAM_ABBREV, OTHER_TEAM_ABBREV)
            
            lane_regex_pattern = f'^([1-{NUM_SWIM_LANES}])'
            teams_pattern = f"({re.escape(MY_TEAM)}|{re.escape(OTHER_TEAM)})"
            abbrev_pattern = f"({re.escape(TEAM_ABBREV)}|{re.escape(OTHER_TEAM_ABBREV)})"
            
            if is_relay:
                relay_lane_matches = list(re.finditer(lane_regex_pattern + r'\s+' + teams_pattern + r'\s+([A-E])\s+' + abbrev_pattern + r'\s+(\d+:\d+\.\d+|\d+\.\d+|NT)', heat_content_cleaned, re.MULTILINE))
                lanes_found = {}
                for m in relay_lane_matches:
                    lane_val = int(m.group(1))
                    relay_letter = m.group(3)
                    team_abr = m.group(4)
                    
                    start_idx = m.end()
                    next_lane_search = re.search(f'^([1-{NUM_SWIM_LANES}])' + r'\s+' + teams_pattern, heat_content_cleaned[start_idx:], re.MULTILINE)
                    end_idx = start_idx + next_lane_search.start() if next_lane_search else len(heat_content_cleaned)
                    swimmer_text = heat_content_cleaned[start_idx:end_idx]
                    
                    swimmers = re.findall(r'([1-4])\)\s*([A-Za-z\s,\'\-\.]+?)\s*(?:\(\d+\))?\s*(' + re.escape(TEAM_ABBREV) + r'\d{3,4}|' + re.escape(OTHER_TEAM_ABBREV) + r'\d{3,4})', swimmer_text)
                    swimmer_dict = {}
                    for s in swimmers:
                        s_num = int(s[0])
                        s_name = s[1].strip()
                        s_ath_num = s[2].strip()
                        swimmer_dict[s_num] = (s_ath_num, s_name)
                        
                    lanes_found[lane_val] = {'TeamAbr': team_abr, 'RelayLetter': relay_letter, 'Swimmers': swimmer_dict}
                    
                for lane in range(1, NUM_SWIM_LANES + 1):
                    if lane in lanes_found:
                        l_data = lanes_found[lane]
                        sw = l_data['Swimmers']
                        parsed_rows.append({
                            'EventNumber': ev_num, 'Heat': heat_num, 'Lane': lane, 'AgeGroup': age_group, 'Stroke': stroke,
                            'TeamAbr': l_data['TeamAbr'], 'RelayLetter': l_data['RelayLetter'],
                            'AthNum1': sw.get(1, (None, None))[0], 'AthName1': sw.get(1, (None, "NO SWIMMER"))[1],
                            'AthNum2': sw.get(2, (None, None))[0], 'AthName2': sw.get(2, (None, None))[1],
                            'AthNum3': sw.get(3, (None, None))[0], 'AthName3': sw.get(3, (None, None))[1],
                            'AthNum4': sw.get(4, (None, None))[0], 'AthName4': sw.get(4, (None, None))[1]
                        })
                    else:
                        parsed_rows.append({
                            'EventNumber': ev_num, 'Heat': heat_num, 'Lane': lane, 'AgeGroup': age_group, 'Stroke': stroke,
                            'TeamAbr': None, 'RelayLetter': None, 'AthNum1': None, 'AthName1': 'NO SWIMMER',
                            'AthNum2': None, 'AthName2': None, 'AthNum3': None, 'AthName3': None, 'AthNum4': None, 'AthName4': None
                        })
            else:
                lanes_found = {}
                raw_lines = heat_content_cleaned.splitlines()
                
                for idx, line in enumerate(raw_lines):
                    line = line.strip()
                    
                    m = re.match(lane_regex_pattern + r'\s+([A-Za-z\s,\'\-\.]+?)\s+' + abbrev_pattern + r'\s*(\d{3,4})', line)
                    if m:
                        lane_val = int(m.group(1))
                        ath_name = m.group(2).strip()
                        team_abr = m.group(3)
                        ath_num = team_abr + m.group(4)
                        lanes_found[lane_val] = (ath_num, ath_name, team_abr)
                        continue
                        
                    m_wrapped = re.match(lane_regex_pattern + r'\s+([A-Za-z\s,\'\-\.]+?)$', line)
                    if m_wrapped and (idx + 1 < len(raw_lines)):
                        next_line = raw_lines[idx + 1].strip()
                        m_id = re.match(r'^' + abbrev_pattern + r'\s*(\d{3,4})', next_line)
                        if m_id:
                            lane_val = int(m_wrapped.group(1))
                            ath_name = m_wrapped.group(2).strip()
                            team_abr = m_id.group(1)
                            ath_num = team_abr + m_id.group(2)
                            lanes_found[lane_val] = (ath_num, ath_name, team_abr)

                for lane in range(1, NUM_SWIM_LANES + 1):
                    if lane in lanes_found:
                        ath_num, ath_name, team_abr = lanes_found[lane]
                        parsed_rows.append({
                            'EventNumber': ev_num, 'Heat': heat_num, 'Lane': lane, 'AgeGroup': age_group, 'Stroke': stroke,
                            'TeamAbr': team_abr, 'RelayLetter': None,
                            'AthNum1': ath_num, 'AthName1': ath_name,
                            'AthNum2': None, 'AthName2': None, 'AthNum3': None, 'AthName3': None, 'AthNum4': None, 'AthName4': None
                        })
                    else:
                        parsed_rows.append({
                            'EventNumber': ev_num, 'Heat': heat_num, 'Lane': lane, 'AgeGroup': age_group, 'Stroke': stroke,
                            'TeamAbr': None, 'RelayLetter': None, 'AthNum1': None, 'AthName1': 'NO SWIMMER',
                            'AthNum2': None, 'AthName2': None, 'AthNum3': None, 'AthName3': None, 'AthNum4': None, 'AthName4': None
                        })

    # ==========================================
    # EXCEL GENERATION & RENAME HEADERS 
    # ==========================================
    df_output = pd.DataFrame(parsed_rows)
    df_output = df_output.rename(columns={'EventNumber': 'Ev', 'Heat': 'HT'})
    
    df_output['TeamAbr2'] = df_output.apply(
        lambda row: row['TeamAbr'] if row['Stroke'] and 'RELAY' in str(row['Stroke']).upper() else "", axis=1
    )

    ICON_REGISTRY = {"SW": "🏄🏻‍♂️", "FC": "🐊", "SC": "🐊"}
    ICON_IMAGE = ICON_REGISTRY.get(TEAM_ABBREV, "🏠")
    df_output['icon'] = df_output['TeamAbr'].apply(lambda x: ICON_IMAGE if x == TEAM_ABBREV else "")

    name_cols = ['AthName1', 'AthName2', 'AthName3', 'AthName4']
    def truncate_and_report(row):
        for col in name_cols:
            if isinstance(row[col], str) and len(row[col]) > 21:
                original = row[col]
                row[col] = original[:21]
                print(f"✂️ Shortened: '{original}' -> '{row[col]}'")
        return row

    df_output = df_output.apply(truncate_and_report, axis=1)
    df_output.to_csv(OUTPUT_EXCEL, index=False)
    print(f"✅ Data extracted and saved to {OUTPUT_EXCEL}")
    
    return df_output

# ==========================================
# 🚀 ENVIRONMENT NAMESPACE AND ORCHESTRATION
# ==========================================
if __name__ == "__main__":
    # 🏠 Weekly Configuration Logs
    TEAM_ABBREV = "SW" 
    INPUT_PDF = 'meetInputSC.pdf'               
    OTHER_TEAM_ABBREV = "SC"                    
    NUM_SWIM_LANES = 6                          

    # 📏 POOL UNIT CONFIGURATION SWITCH (Set to either "YARD" or "METER")
    POOL_UNITS = "METER"
    POOL_UNITS = "YARD"

    TEMPLATE_MODE = "4x6" # Change this to "8.5x11" whenever you need to swap
    TEMPLATE_MODE = "8.5x11" # Change this to "8.5x11" whenever you need to swap

    # 🗺️ Master League Team Registry Dictionary
    LEAGUE_TEAMS = {
        "FC": "FC Gators",
        "FG": "FC Gold",
        "CP": "Commonwealth",
        "CW": "CWST",
        "GG": "GreatwoodGeysers",
        "LO": "Lake Olympia",
        "ME": "Meadows Marlins",
        "MW": "Maplewood Marlins",
        "NT": "NT Tarpons",
        "NW": "Torpedoes",
        "OR": "Houston Orcas",
        "PG": "Pecan Grove",
        "SC": "SC Gators",
        "SH": "Sharpstown",
        "SL": "Sugar Land Shark",
        "SK": "Shadow Creek",
        "SP": "Sienna Stingrays",
        "ST": "Stafford Stingrays",
        "SW": "SW Surfers",
        "TR": "Teal Run",
        "WH": "Glenshire Wahoo"
    }

    OUTPUT_EXCEL = f'meet_entries_{TEAM_ABBREV}_v_{OTHER_TEAM_ABBREV}.csv'

    EVENT_YARD = {
        1: {'AgeGroup': 'Girls 6 & Under', 'Stroke': '100YD FREE RELAY'},
        2: {'AgeGroup': 'Boys 6 & Under', 'Stroke': '100YD FREE RELAY'},
        3: {'AgeGroup': 'Girls 8 & Under', 'Stroke': '100YD MEDLEY'},
        4: {'AgeGroup': 'Boys 8 & Under', 'Stroke': '100YD MEDLEY'},
        5: {'AgeGroup': 'Girls 9-10', 'Stroke': '100YD MEDLEY'},
        6: {'AgeGroup': 'Boys 9-10', 'Stroke': '100YD MEDLEY'},
        7: {'AgeGroup': 'Girls 11-12', 'Stroke': '100YD MEDLEY'},
        8: {'AgeGroup': 'Boys 11-12', 'Stroke': '100YD MEDLEY'},
        9: {'AgeGroup': 'Girls 13-14', 'Stroke': '100YD MEDLEY'},
        10: {'AgeGroup': 'Boys 13-14', 'Stroke': '100YD MEDLEY'},
        11: {'AgeGroup': 'Women 15-18', 'Stroke': '100YD MEDLEY'},
        12: {'AgeGroup': 'Men 15-18', 'Stroke': '100YD MEDLEY'},
        13: {'AgeGroup': 'Girls 11-12', 'Stroke': '100YD IM'},
        14: {'AgeGroup': 'Boys 11-12', 'Stroke': '100YD IM'},
        15: {'AgeGroup': 'Girls 13-14', 'Stroke': '100YD IM'},
        16: {'AgeGroup': 'Boys 13-14', 'Stroke': '100YD IM'},
        17: {'AgeGroup': 'Women 15-18', 'Stroke': '100YD IM'},
        18: {'AgeGroup': 'Men 15-18', 'Stroke': '100YD IM'},
        19: {'AgeGroup': 'Girls 6 & Under', 'Stroke': '25YD FREESTYLE'},
        20: {'AgeGroup': 'Boys 6 & Under', 'Stroke': '25YD FREESTYLE'},
        21: {'AgeGroup': 'Girls 7-8', 'Stroke': '25YD FREESTYLE'},
        22: {'AgeGroup': 'Boys 7-8', 'Stroke': '25YD FREESTYLE'},
        23: {'AgeGroup': 'Girls 9-10', 'Stroke': '25YD FREESTYLE'},
        24: {'AgeGroup': 'Boys 9-10', 'Stroke': '25YD FREESTYLE'},
        25: {'AgeGroup': 'Girls 11-12', 'Stroke': '50YD FREESTYLE'},
        26: {'AgeGroup': 'Boys 11-12', 'Stroke': '50YD FREESTYLE'},
        27: {'AgeGroup': 'Girls 13-14', 'Stroke': '50YD FREESTYLE'},
        28: {'AgeGroup': 'Boys 13-14', 'Stroke': '50YD FREESTYLE'},
        29: {'AgeGroup': 'Women 15-18', 'Stroke': '50YD FREESTYLE'},
        30: {'AgeGroup': 'Men 15-18', 'Stroke': '50YD FREESTYLE'},
        31: {'AgeGroup': 'Girls 8 & Under', 'Stroke': '25YD BREAST'},
        32: {'AgeGroup': 'Boys 8 & Under', 'Stroke': '25YD BREAST'},
        33: {'AgeGroup': 'Girls 9-10', 'Stroke': '25YD BREAST'},
        34: {'AgeGroup': 'Boys 9-10', 'Stroke': '25YD BREAST'},
        35: {'AgeGroup': 'Girls 11-12', 'Stroke': '50YD BREAST'},
        36: {'AgeGroup': 'Boys 11-12', 'Stroke': '50YD BREAST'},
        37: {'AgeGroup': 'Girls 13-14', 'Stroke': '50YD BREAST'},
        38: {'AgeGroup': 'Boys 13-14', 'Stroke': '50YD BREAST'},
        39: {'AgeGroup': 'Women 15-18', 'Stroke': '50YD BREAST'},
        40: {'AgeGroup': 'Men 15-18', 'Stroke': '50YD BREAST'},
        41: {'AgeGroup': 'Girls 8 & Under', 'Stroke': '25YD BACKSTROKE'},
        42: {'AgeGroup': 'Boys 8 & Under', 'Stroke': '25YD BACKSTROKE'},
        43: {'AgeGroup': 'Girls 9-10', 'Stroke': '25YD BACKSTROKE'},
        44: {'AgeGroup': 'Boys 9-10', 'Stroke': '25YD BACKSTROKE'},
        45: {'AgeGroup': 'Girls 11-12', 'Stroke': '50YD BACKSTROKE'},
        46: {'AgeGroup': 'Boys 11-12', 'Stroke': '50YD BACKSTROKE'},
        47: {'AgeGroup': 'Girls 13-14', 'Stroke': '50YD BACKSTROKE'},
        48: {'AgeGroup': 'Boys 13-14', 'Stroke': '50YD BACKSTROKE'},
        49: {'AgeGroup': 'Women 15-18', 'Stroke': '50YD BACKSTROKE'},
        50: {'AgeGroup': 'Men 15-18', 'Stroke': '50YD BACKSTROKE'},
        51: {'AgeGroup': 'Girls 8 & Under', 'Stroke': '25YD BUTTERFLY'},
        52: {'AgeGroup': 'Boys 8 & Under', 'Stroke': '25YD BUTTERFLY'},
        53: {'AgeGroup': 'Girls 9-10', 'Stroke': '25YD BUTTERFLY'},
        54: {'AgeGroup': 'Boys 9-10', 'Stroke': '25YD BUTTERFLY'},
        55: {'AgeGroup': 'Girls 11-12', 'Stroke': '50YD BUTTERFLY'},
        56: {'AgeGroup': 'Boys 11-12', 'Stroke': '50YD BUTTERFLY'},
        57: {'AgeGroup': 'Girls 13-14', 'Stroke': '50YD BUTTERFLY'},
        58: {'AgeGroup': 'Boys 13-14', 'Stroke': '50YD BUTTERFLY'},
        59: {'AgeGroup': 'Women 15-18', 'Stroke': '50YD BUTTERFLY'},
        60: {'AgeGroup': 'Men 15-18', 'Stroke': '50YD BUTTERFLY'},
        61: {'AgeGroup': 'Girls 7-8', 'Stroke': '100YD FREE RELAY'},
        62: {'AgeGroup': 'Boys 7-8', 'Stroke': '100YD FREE RELAY'},
        63: {'AgeGroup': 'Girls 9-10', 'Stroke': '100YD FREE RELAY'},
        64: {'AgeGroup': 'Boys 9-10', 'Stroke': '100YD FREE RELAY'},
        65: {'AgeGroup': 'Girls 11-12', 'Stroke': '100YD FREE RELAY'},
        66: {'AgeGroup': 'Boys 11-12', 'Stroke': '100YD FREE RELAY'},
        67: {'AgeGroup': 'Girls 13-14', 'Stroke': '100YD FREE RELAY'},
        68: {'AgeGroup': 'Boys 13-14', 'Stroke': '100YD FREE RELAY'},
        69: {'AgeGroup': 'Women 15-18', 'Stroke': '100YD FREE RELAY'},
        70: {'AgeGroup': 'Men 15-18', 'Stroke': '100YD FREE RELAY'}
    }

    EVENT_METER = {
        1: {'AgeGroup': 'Girls 6 & Under', 'Stroke': '100M FREE RELAY'},
        2: {'AgeGroup': 'Boys 6 & Under', 'Stroke': '100M FREE RELAY'},
        3: {'AgeGroup': 'Girls 8 & Under', 'Stroke': '100M MEDLEY RELAY'},
        4: {'AgeGroup': 'Boys 8 & Under', 'Stroke': '100M MEDLEY RELAY'},
        5: {'AgeGroup': 'Girls 9-10', 'Stroke': '100M MEDLEY RELAY'},
        6: {'AgeGroup': 'Boys 9-10', 'Stroke': '100M MEDLEY RELAY'},
        7: {'AgeGroup': 'Girls 11-12', 'Stroke': '100M MEDLEY RELAY'},
        8: {'AgeGroup': 'Boys 11-12', 'Stroke': '100M MEDLEY RELAY'},
        9: {'AgeGroup': 'Girls 13-14', 'Stroke': '100M MEDLEY RELAY'},
        10: {'AgeGroup': 'Boys 13-14', 'Stroke': '100M MEDLEY RELAY'},
        11: {'AgeGroup': 'Women 15-18', 'Stroke': '100M MEDLEY RELAY'},
        12: {'AgeGroup': 'Men 15-18', 'Stroke': '100M MEDLEY RELAY'},
        13: {'AgeGroup': 'Girls 11-12', 'Stroke': '100M IM'},
        14: {'AgeGroup': 'Boys 11-12', 'Stroke': '100M IM'},
        15: {'AgeGroup': 'Girls 13-14', 'Stroke': '100M IM'},
        16: {'AgeGroup': 'Boys 13-14', 'Stroke': '100M IM'},
        17: {'AgeGroup': 'Women 15-18', 'Stroke': '100M IM'},
        18: {'AgeGroup': 'Men 15-18', 'Stroke': '100M IM'},
        19: {'AgeGroup': 'Girls 6 & Under', 'Stroke': '25M FREESTYLE'},
        20: {'AgeGroup': 'Boys 6 & Under', 'Stroke': '25M FREESTYLE'},
        21: {'AgeGroup': 'Girls 7-8', 'Stroke': '25M FREESTYLE'},
        22: {'AgeGroup': 'Boys 7-8', 'Stroke': '25M FREESTYLE'},
        23: {'AgeGroup': 'Girls 9-10', 'Stroke': '25M FREESTYLE'},
        24: {'AgeGroup': 'Boys 9-10', 'Stroke': '25M FREESTYLE'},
        25: {'AgeGroup': 'Girls 11-12', 'Stroke': '50M FREESTYLE'},
        26: {'AgeGroup': 'Boys 11-12', 'Stroke': '50M FREESTYLE'},
        27: {'AgeGroup': 'Girls 13-14', 'Stroke': '50M FREESTYLE'},
        28: {'AgeGroup': 'Boys 13-14', 'Stroke': '50M FREESTYLE'},
        29: {'AgeGroup': 'Women 15-18', 'Stroke': '50M FREESTYLE'},
        30: {'AgeGroup': 'Men 15-18', 'Stroke': '50M FREESTYLE'},
        31: {'AgeGroup': 'Girls 8 & Under', 'Stroke': '25M BREAST'},
        32: {'AgeGroup': 'Boys 8 & Under', 'Stroke': '25M BREAST'},
        33: {'AgeGroup': 'Girls 9-10', 'Stroke': '25M BREAST'},
        34: {'AgeGroup': 'Boys 9-10', 'Stroke': '25M BREAST'},
        35: {'AgeGroup': 'Girls 11-12', 'Stroke': '50M BREAST'},
        36: {'AgeGroup': 'Boys 11-12', 'Stroke': '50M BREAST'},
        37: {'AgeGroup': 'Girls 13-14', 'Stroke': '50M BREAST'},
        38: {'AgeGroup': 'Boys 13-14', 'Stroke': '50M BREAST'},
        39: {'AgeGroup': 'Women 15-18', 'Stroke': '50M BREAST'},
        40: {'AgeGroup': 'Men 15-18', 'Stroke': '50M BREAST'},
        41: {'AgeGroup': 'Girls 8 & Under', 'Stroke': '25M BACKSTROKE'},
        42: {'AgeGroup': 'Boys 8 & Under', 'Stroke': '25M BACKSTROKE'},
        43: {'AgeGroup': 'Girls 9-10', 'Stroke': '25M BACKSTROKE'},
        44: {'AgeGroup': 'Boys 9-10', 'Stroke': '25M BACKSTROKE'},
        45: {'AgeGroup': 'Girls 11-12', 'Stroke': '50M BACKSTROKE'},
        46: {'AgeGroup': 'Boys 11-12', 'Stroke': '50M BACKSTROKE'},
        47: {'AgeGroup': 'Girls 13-14', 'Stroke': '50M BACKSTROKE'},
        48: {'AgeGroup': 'Boys 13-14', 'Stroke': '50M BACKSTROKE'},
        49: {'AgeGroup': 'Women 15-18', 'Stroke': '50M BACKSTROKE'},
        50: {'AgeGroup': 'Men 15-18', 'Stroke': '50M BACKSTROKE'},
        51: {'AgeGroup': 'Girls 8 & Under', 'Stroke': '25M BUTTERFLY'},
        52: {'AgeGroup': 'Boys 8 & Under', 'Stroke': '25M BUTTERFLY'},
        53: {'AgeGroup': 'Girls 9-10', 'Stroke': '25M BUTTERFLY'},
        54: {'AgeGroup': 'Boys 9-10', 'Stroke': '25M BUTTERFLY'},
        55: {'AgeGroup': 'Girls 11-12', 'Stroke': '50M BUTTERFLY'},
        56: {'AgeGroup': 'Boys 11-12', 'Stroke': '50M BUTTERFLY'},
        57: {'AgeGroup': 'Girls 13-14', 'Stroke': '50M BUTTERFLY'},
        58: {'AgeGroup': 'Boys 13-14', 'Stroke': '50M BUTTERFLY'},
        59: {'AgeGroup': 'Women 15-18', 'Stroke': '50M BUTTERFLY'},
        60: {'AgeGroup': 'Men 15-18', 'Stroke': '50M BUTTERFLY'},
        61: {'AgeGroup': 'Girls 7-8', 'Stroke': '100M FREE RELAY'},
        62: {'AgeGroup': 'Boys 7-8', 'Stroke': '100M FREE RELAY'},
        63: {'AgeGroup': 'Girls 9-10', 'Stroke': '100M FREE RELAY'},
        64: {'AgeGroup': 'Boys 9-10', 'Stroke': '100M FREE RELAY'},
        65: {'AgeGroup': 'Girls 11-12', 'Stroke': '100M FREE RELAY'},
        66: {'AgeGroup': 'Boys 11-12', 'Stroke': '100M FREE RELAY'},
        67: {'AgeGroup': 'Girls 13-14', 'Stroke': '100M FREE RELAY'},
        68: {'AgeGroup': 'Boys 13-14', 'Stroke': '100M FREE RELAY'},
        69: {'AgeGroup': 'Women 15-18', 'Stroke': '100M FREE RELAY'},
        70: {'AgeGroup': 'Men 15-18', 'Stroke': '100M FREE RELAY'}
    }

    # 🎛️ VALIDATION LOGIC: Auto-assign right registry block based on configuration choice
    if str(POOL_UNITS).strip().upper() == "YARD":
        ACTIVE_REGISTRY = EVENT_YARD
        print("📏 Pool Settings: Configured for YARDS registry matrix.")
    else:
        ACTIVE_REGISTRY = EVENT_METER
        print("📏 Pool Settings: Configured for METERS registry matrix.")

    OTHER_TEAM = LEAGUE_TEAMS.get(OTHER_TEAM_ABBREV, "Unknown-Opponent")
    MY_TEAM = LEAGUE_TEAMS.get(TEAM_ABBREV, "Unknown-Home-Team")

    # 1️⃣ Execute the data parser matrix and receive the structured dataset block
    extracted_df = weekly_swim_parser(
        TEAM_ABBREV=TEAM_ABBREV, INPUT_PDF=INPUT_PDF, OTHER_TEAM_ABBREV=OTHER_TEAM_ABBREV,
        NUM_SWIM_LANES=NUM_SWIM_LANES, LEAGUE_TEAMS=LEAGUE_TEAMS, OUTPUT_EXCEL=OUTPUT_EXCEL,
        EVENT_REGISTRY=ACTIVE_REGISTRY, OTHER_TEAM=OTHER_TEAM, MY_TEAM=MY_TEAM
    )
    
    # 2️⃣ Forward the returned DataFrame cleanly into the headless HTML compiler loop
    if extracted_df is not None:
        generate_html_lane_cards(
            extracted_df, 
            TEAM_ABBREV=TEAM_ABBREV, 
            OTHER_TEAM_ABBREV=OTHER_TEAM_ABBREV, 
            mode=TEMPLATE_MODE
        )