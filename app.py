import streamlit as st
import os
import re
import csv
from google import genai
from google.genai import types

# Set up page configurations for a clean, modern dashboard
st.set_page_config(
    page_title="Lehigh Instrument Concierge", 
    page_icon="🔬", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize the Gemini Client securely
# It automatically picks up the 'GEMINI_API_KEY' from your environment/secrets
try:
    client = genai.Client()
except Exception:
    client = None

# =====================================================================
# MODULE 1: DATA PIPELINE ENGINE
# =====================================================================
CAPABILITY_DICTIONARY = {
    'microscope': 'High-resolution imaging, microscopy, optical/fluorescence sample analysis, and structural surface characterization.',
    'confocal': 'Confocal laser scanning microscopy: Optimized for high-speed, 3D optical sectioning of biological tissues and material topography.',
    'nmr': 'Nuclear Magnetic Resonance (NMR) spectroscopy: Non-destructive structural mapping, chemical kinetics, molecular fluid dynamics, and organic tracking.',
    'spectrometer': 'Spectroscopic analysis, materials light absorption/emission configuration, analytical identification, and chemical molecular profiling.',
    'spectro': 'Analytical spectroscopy, wave-profile identification, atomic emission tracking, or mass configuration validation.',
    'afm': 'Atomic Force Microscopy (AFM): Nanoscale three-dimensional surface topographical mapping, absolute roughness, and localized physical mechanical properties.',
    'raman': 'Raman Spectroscopy: Non-destructive chemical composition mapping, structural fingerprinting, crystalline phase identification, and molecular bond configurations.',
    'xrd': 'X-Ray Diffraction (XRD): Deep identification of material crystalline structures, phase identification, lattice orientation, and thin-film compositions.',
    'diffractometer': 'X-Ray Diffraction (XRD) phase orientation tracking, crystal lattice validation, and advanced powder analysis.',
    'mass': 'Mass Spectrometry: Ultra-precise compound mass-to-charge ratios, sequence determination, biomolecule mass testing, and trace elemental discovery.',
    'lc-ms': 'Liquid Chromatography Mass Spectrometry: Advanced physical compound separation linked with deep analytical trace verification.',
    'sorter': 'Automated high-speed flow-cytometry cell sorting, fluorescence identification channels, and sterile cellular sample fractionation.',
    'furn': 'High-temperature thermal treatment chambers, sintering systems, physical phase transition testing, and thermal processing.',
    'mill': 'Precision specimen thinning, focused ion milling, surface polishing, and clean sample sectioning for transmission electron microscopy (TEM).',
    'calorimeter': 'Differential scanning thermal evaluation, precise heat-flow transition points, enthalpy profiles, and heat capacity tracking.',
    'seismology': 'Geophysical seismic wave tracking, acoustic vibration modeling, crustal stress testing, and real-time planetary acoustic measurements.',
    'isotope': 'Stable isotope ratio monitoring, mass verification for environmental tracking, carbon/nitrogen footprint mapping, and paleo-climate forensics.',
    'structural': 'Large-scale structural safety engineering testing, high-capacity load frame dynamics, and real-time stress/strain fatigue evaluation.'
}

def is_valid_cell(value):
    if not value:
        return False
    val_clean = str(value).strip().upper()
    return val_clean not in ['', 'NAN', 'NULL', 'NONE']

def format_email(computing_id):
    if not is_valid_cell(computing_id):
        return "N/A - Contact Department Admin"
    id_clean = str(computing_id).strip()
    if "@" in id_clean:
        return id_clean.lower()
    return f"{id_clean.lower()}@lehigh.edu"

@st.cache_data
def bootstrap_and_load_data():
    source_csv_path = "Lehigh_Instrumentation_Master_List_v2 (1).csv"
    if not os.path.exists(source_csv_path):
        return None, 0
        
    enriched_database = []
    offline_count = 0
    
    with open(source_csv_path, mode='r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            index_num = row.get('Index', '').strip()
            title = row.get('Index Title', '').strip()
            asset_id = row.get('Asset_Number', '').strip()
            building = row.get('Building', '').strip() or "Main Campus Core Facility"
            room = row.get('Room No', '').strip() or "Contact Admin"
            dept_title = row.get('Department Title', '').strip() or "General Academic Support"
            
            title_lower = title.lower()
            if any(kwd in title_lower for kwd in ['offline', 'decommissioned', 'closed', 'surplus', 'inactive']):
                offline_count += 1
                continue 
                
            tech_poc = row.get('Technical POC', '').strip()
            faculty_poc = row.get('Faculty POC', '').strip()
            financial_poc = row.get('Financial POC', '').strip()
            financial_mgr = row.get('Financial_Manager', '').strip()
            
            tech_email_col = row.get('Technician email', '').strip()
            fac_email_col = row.get('Faculty Email', '').strip()
            financial_email_col = row.get('Financial_Manager Email', '').strip()
            
            financial_names = set()
            for f_val in [financial_poc, financial_mgr]:
                if is_valid_cell(f_val):
                    financial_names.add(str(f_val).strip().lower())
            
            resolved_poc_name = "Department Operations Administrator"
            poc_role_label = "Departmental Lead"
            resolved_email_id = ""
            requires_accessibility_warning = False
            
            # ACCESS HIERARCHY RULES
            if is_valid_cell(tech_poc) and str(tech_poc).lower() not in financial_names:
                resolved_poc_name = tech_poc
                poc_role_label = "Technical Point of Contact"
                resolved_email_id = tech_email_col
            elif is_valid_cell(faculty_poc):
                resolved_poc_name = faculty_poc
                poc_role_label = "Faculty Point of Contact / Principal Investigator"
                resolved_email_id = fac_email_col
            elif is_valid_cell(financial_poc) or is_valid_cell(financial_mgr):
                resolved_poc_name = financial_poc if is_valid_cell(financial_poc) else financial_mgr
                poc_role_label = "Financial Manager / Account Custodian"
                resolved_email_id = financial_email_col
                requires_accessibility_warning = True
            
            raw_desc = row.get('Capability Description', '').strip()
            is_generic = (not is_valid_cell(raw_desc) or "Contact Technical POC" in raw_desc or len(raw_desc) < 5)
            
            final_capability = raw_desc if not is_generic else "Experimental research capability."
            if is_generic:
                for keyword, description in CAPABILITY_DICTIONARY.items():
                    if keyword in title_lower:
                        final_capability = description
                        break
            
            enriched_database.append({
                "index_account": index_num,
                "instrument_name": title,
                "asset_id": asset_id if is_valid_cell(asset_id) else "University Tagged/Pending",
                "department": dept_title,
                "location": f"{building}, Room {room}",
                "contact_person": resolved_poc_name,
                "contact_role": poc_role_label,
                "contact_email": format_email(resolved_email_id),
                "accessibility_warning": requires_accessibility_warning,
                "capabilities": final_capability,
                "search_blob": f"{title} {dept_title} {building} {final_capability} {resolved_poc_name}".lower()
            })
            
    return enriched_database, offline_count

# Load the structured data
db, offline_filtered = bootstrap_and_load_data()

# =====================================================================
# MODULE 2: GRAPHICAL USER INTERFACE NAVIGATION PANELS
# =====================================================================
st.title("🔬 Lehigh University Research Instrumentation Concierge")
st.markdown("Verify operational analytical capabilities across university equipment portfolios and coordinate access routing paths.")

if db is None:
    st.error("⚠️ Data file structural pipeline failure. Please bundle `Lehigh_Instrumentation_Master_List_v2 (1).csv` alongside this `app.py` script file.")
else:
    # Sidebar layout status
    st.sidebar.header("Core Infrastructure")
    st.sidebar.info(f"🟢 Active Assets: {len(db)}")
    st.sidebar.warning(f"🔴 Offline Filtered: {offline_filtered}")
    
    # Create Layout Tabs for the two separate functionalities
    tab1, tab2 = st.tabs(["🔍 Hardware Directory (Keyword Search)", "🤖 AI Experiment Explorer (Natural Language)"])
    
    # -----------------------------------------------------------------
    # TAB 1: EXACT MATCH DIRECTORY (YOUR ORIGINAL FUNCTIONALITY)
    # -----------------------------------------------------------------
    with tab1:
        st.markdown("### Exact Asset & Keyword Query")
        query = st.text_input("💬 Enter specific equipment short names, locations, or manager last names:", 
                             placeholder="e.g., Seismology, Lee Graham, XRD, Confocal Microscope...", key="dir_search")

        if query:
            tokens = [t.lower() for t in re.findall(r'\w+', query) if len(t) > 2]
            matches = []
            
            if tokens:
                for item in db:
                    score = 0
                    blob = item["search_blob"]
                    name_lower = item["instrument_name"].lower()
                    
                    for token in tokens:
                        if token in name_lower:
                            score += 15
                        elif token in blob:
                            score += 5
                    if score > 0:
                        matches.append((score, item))
                
                matches.sort(key=lambda x: x[0], reverse=True)
                matches = [record for score, record in matches[:10]]

            if not matches:
                st.info(f"🤖 No direct matching instrumentation indices identified for: \"{query}\"")
            else:
                for item in matches:
                    with st.container(border=True):
                        col1, col2 = st.columns([3, 2])
                        with col1:
                            st.markdown(f"### 📍 {item['instrument_name']}")
                            st.markdown(f"**Department:** {item['department']}")
                            st.markdown(f"**Location:** {item['location']}")
                            st.markdown(f"💡 **Capabilities:** {item['capabilities']}")
                        with col2:
                            st.markdown("#### Operational Contact Details")
                            st.markdown(f"👤 **Name:** **{item['contact_person']}**")
                            st.markdown(f"🏷️ **Role:** *{item['contact_role']}*")
                            st.markdown(f"✉️ **Email:** [{item['contact_email']}](mailto:{item['contact_email']})")
                            st.markdown(f"💳 **Billing Index:** `{item['index_account']}`")
                        if item["accessibility_warning"]:
                            st.warning("⚠️ **Accessibility Warning:** No active Technical or Faculty Point of Contact is registered for this instrument. The contact provided above is a Financial Manager. The equipment might be locked, offline, or restricted to a specific user group, and may not be accessible for general campus student research.")

    # -----------------------------------------------------------------
    # TAB 2: AI EXPERIMENT EXPLORER (THE NEW GEMINI SEARCH FUNCTION)
    # -----------------------------------------------------------------
    with tab2:
        st.markdown("### Natural Language Experiment Translation")
        st.write("Don't know what machine you need? Describe your scientific target, target material, or data requirements below, and Gemini will find matching Lehigh assets.")
        
        user_experiment = st.text_area("🔬 Describe your experiment proposal or analytical data goals:", 
                                       placeholder="e.g., I need to find the chemical elements inside an organic sample without destroying it, or I am trying to map high-speed cell fractionation tags...",
                                       key="ai_text")
        
        if st.button("🚀 Ask Gemini Concierge", type="primary"):
            if not client:
                st.error("🔑 Gemini Client Initialization Failure. Please verify your `GEMINI_API_KEY` environment token is set.")
            elif not user_experiment.strip():
                st.warning("Please type an experimental summary before running the evaluation agent.")
            else:
                with st.spinner("Analyzing laboratory portfolio matrices..."):
                    # Build contextual reference block out of your script mappings
                    capabilities_context = "\n".join([f"- Keyword '{k}': {v}" for k, v in CAPABILITY_DICTIONARY.items()])
                    
                    # Programmatic AI Prompt instructing the layout mapping rules
                    system_instruction = (
                        "You are the Lehigh University Engineering Core Facility Concierge Bot. "
                        "Your goal is to parse a student's high-level research proposal and determine if any campus equipment matches their intent. "
                        "Analyze their request against our active campus capability keywords:\n"
                        f"{capabilities_context}\n\n"
                        "CRITICAL OUTPUT INSTRUCTIONS:\n"
                        "1. If you find a good match, name the category keyword clearly (e.g., 'Raman Spectroscopy', 'AFM', 'NMR') and explain why it fits their experiment.\n"
                        "2. Provide 2-3 specific instructional next steps for what search strings they should run inside the Directory tab to look up exact lab managers.\n"
                        "3. If their request is fundamentally outside our campus portfolio capabilities, explicitly state: 'I could not identify an ideal asset fit for this target setup on campus' and suggest alternative general testing methods."
                    )
                    
                    try:
                        # Request inference from Gemini 2.5 Flash
                        response = client.models.generate_content(
                            model='gemini-2.5-flash',
                            contents=user_experiment,
                            config=types.GenerateContentConfig(
                                system_instruction=system_instruction,
                                temperature=0.2 # Lower temperature guarantees stricter, evidence-based reasoning
                            )
                        )
                        
                        st.markdown("### 🤖 Concierge AI Recommendations")
                        st.info(response.text)
                        
                    except Exception as e:
                        st.error(f"AI Matrix Generation Error: {str(e)}")
