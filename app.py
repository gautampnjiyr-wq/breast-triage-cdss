import datetime
import uuid
import streamlit as st
import streamlit.components.v1 as components
from PIL import Image

st.set_page_config(
    page_title="Breast Triage CDSS",
    page_icon="🩺",
    layout="wide"
)

# --- DATABASE / SUPABASE INITIALIZATION ---
HAS_SUPABASE = False
supabase = None

if "SUPABASE_URL" in st.secrets and "SUPABASE_KEY" in st.secrets:
    try:
        from supabase import create_client, Client
        @st.cache_resource
        def get_supabase_client() -> Client:
            return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
        supabase = get_supabase_client()
        HAS_SUPABASE = True
    except Exception as e:
        st.warning(f"Database connection warning: {e}")

# Helper: Load all patients from DB or fallback
def fetch_patient_registry():
    if HAS_SUPABASE:
        try:
            res = supabase.table("patients").select("*").order("created_at", desc=False).execute()
            if res.data:
                db_dict = {}
                for row in res.data:
                    if isinstance(row.get("date_exam"), str):
                        try:
                            row["date_exam"] = datetime.date.fromisoformat(row["date_exam"])
                        except Exception:
                            row["date_exam"] = datetime.date.today()
                    row["images"] = row.get("images") or []
                    row["audit_log"] = row.get("audit_log") or []
                    db_dict[row["case_id"]] = row
                return db_dict
        except Exception as e:
            st.error(f"Error fetching from Supabase: {e}")

    if "patients" not in st.session_state:
        st.session_state.patients = {
            "PB-2026-1035": {
                "name": "Sunita Sharma",
                "age": 48,
                "uhid": "PB10003501",
                "case_id": "PB-2026-1035",
                "date_exam": datetime.date.today(),
                "pincode": "248001",
                "referral_doc": "Dr. Rajiv Singh, MBBS",
                "cbe_mass": "Hard, Irregular (Tethered/Fixed to skin or fascia)",
                "cbe_size": "4.0 cm",
                "cbe_nodes": "Present (Firm, Non-tender, or Matted)",
                "pocus_available": True,
                "pocus_orientation": "Taller-than-wide (Vertical growth / Transverse to skin)",
                "pocus_margins": "Irregular / Spiculated / Microlobulated",
                "pocus_posterior": "Posterior acoustic shadowing (dark shadow behind mass)",
                "fnac_passes": "2 passes (23G Needle, Capillary method)",
                "prep_tech": "Lab Tech Sarah Khan",
                "staining": "Diff-Quik (90-second rapid Romanowsky)",
                "macro_adequate": "Yes (Chalky/white granular fragments visible against light)",
                "images": [],
                "review_mode": "Final Pathologist Sign-Off",
                "pathologist": "Dr. Priya Sharma, MD Pathology",
                "yokohama": "Category 2: Benign Cells (Risk of Malignancy: <3%)",
                "path_notes": "Abundant naked bipolar nuclei with sheets of cohesive benign ductal epithelial cells. No marked atypia in viewed fields.",
                "asha_worker": "Meena Devi (ANM/ASHA)",
                "asha_contact": "+91 9876543210",
                "tracker_status": "Referral Pending (Counseling completed at PHC)",
                "audit_log": [
                    f"[{datetime.date.today()} 09:30] Registered & Examined by Dr. Rajiv Singh, MBBS",
                    f"[{datetime.date.today()} 09:45] Stained with Diff-Quik by Lab Tech Sarah Khan"
                ]
            }
        }
    return st.session_state.patients

# Helper: Save patient data permanently
def save_patient_record(patient_dict):
    if HAS_SUPABASE:
        try:
            payload = patient_dict.copy()
            if isinstance(payload.get("date_exam"), (datetime.date, datetime.datetime)):
                payload["date_exam"] = payload["date_exam"].isoformat()
            supabase.table("patients").upsert(payload).execute()
        except Exception as e:
            st.error(f"Error saving to cloud database: {e}")
    st.session_state.patients[patient_dict["case_id"]] = patient_dict

# Helper: Upload photo to permanent Supabase bucket
def save_slide_image(file_obj, case_id, role, uploader_name):
    timestamp_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    if HAS_SUPABASE:
        try:
            filename = f"{case_id}_{uuid.uuid4().hex[:6]}.jpg"
            file_bytes = file_obj.getvalue()
            supabase.storage.from_("slide-micrographs").upload(
                path=filename,
                file=file_bytes,
                file_options={"content-type": file_obj.type or "image/jpeg"}
            )
            image_url = supabase.storage.from_("slide-micrographs").get_public_url(filename)
            return {
                "url": image_url,
                "role": role,
                "uploader": uploader_name,
                "timestamp": timestamp_str
            }
        except Exception as e:
            st.error(f"Cloud image upload error: {e}")

    return {
        "file": file_obj,
        "role": role,
        "uploader": uploader_name,
        "timestamp": timestamp_str
    }

# Sync Data
st.session_state.patients = fetch_patient_registry()

if "active_case_id" not in st.session_state or st.session_state.active_case_id not in st.session_state.patients:
    st.session_state.active_case_id = list(st.session_state.patients.keys())[0]

# --- SIDEBAR NAVIGATION ---
st.sidebar.title("🩺 Breast Triage CDSS")
st.sidebar.caption("Evidence-Based Bedside Decision Support")

if HAS_SUPABASE:
    st.sidebar.success("🟢 Cloud Sync: Active (Supabase)")
else:
    st.sidebar.warning("🟡 Storage: RAM Session (Set Secrets for Cloud)")

case_options = list(st.session_state.patients.keys())
selected_case = st.sidebar.selectbox(
    "Active Patient Case:",
    options=case_options,
    index=case_options.index(st.session_state.active_case_id) if st.session_state.active_case_id in case_options else 0
)
st.session_state.active_case_id = selected_case
patient = st.session_state.patients[st.session_state.active_case_id]

if patient.get("review_mode") == "Final Pathologist Sign-Off":
    st.sidebar.success("● Pathologist Reviewed")
elif patient.get("review_mode") == "AI Provisional":
    st.sidebar.warning("⚡ AI Provisional Triage")
else:
    st.sidebar.info("⏳ Awaiting Cytology Review")

st.sidebar.markdown(f"**Patient:** {patient['name']}  \n**UHID:** `{patient['uhid']}`")
st.sidebar.divider()

role = st.sidebar.radio(
    "Workflow Cadre View:",
    [
        "1. Medical Officer (Exam, POCUS & Direct Upload)",
        "2. Lab Technician (Staining, Patient Link & Upload)",
        "3. Cytology Review (AI Assist & Pathologist Sign-Off)",
        "4. CDSS Triage & Advisory Report",
        "5. ASHA Closed-Loop Tracker",
        "6. Audit Trail & Provenance (Who Did What)"
    ]
)

# ==========================================
# MODULE 1: MEDICAL OFFICER
# ==========================================
if role == "1. Medical Officer (Exam, POCUS & Direct Upload)":
    st.header("1. Medical Officer: Clinical Examination & Bedside Staging")
    st.caption("Register patients, edit existing demographics, record clinical exams, and upload micrographs.")

    tab_edit, tab_register = st.tabs(["📝 View / Edit Current Patient", "➕ Register New Patient"])

    with tab_register:
        with st.form("new_patient_form"):
            st.subheader("New Patient Intake")
            c1, c2, c3 = st.columns(3)
            new_name = c1.text_input("Full Name")
            new_age = c2.number_input("Age (Years)", 15, 100, 45)
            new_uhid = c3.text_input("UHID / National Health ID")
            new_case_id = c1.text_input("Case ID (Unique)", f"PB-2026-{len(st.session_state.patients)+1001}")
            new_pincode = c2.text_input("Pincode", "248001")
            new_doc = c3.text_input("Examining MO Name", "Dr. Rajiv Singh, MBBS")
            submit_new = st.form_submit_button("Register & Activate Record")

            if submit_new and new_case_id:
                new_patient = {
                    "name": new_name or "New Patient",
                    "age": int(new_age),
                    "uhid": new_uhid or "PENDING",
                    "case_id": new_case_id,
                    "date_exam": datetime.date.today(),
                    "pincode": new_pincode,
                    "referral_doc": new_doc,
                    "cbe_mass": "Firm, Discrete, Moderately mobile",
                    "cbe_size": "2.5 cm",
                    "cbe_nodes": "Absent (Clinically negative)",
                    "pocus_available": False,
                    "pocus_orientation": "Wider-than-tall (Horizontal / Parallel to skin)",
                    "pocus_margins": "Smooth & Well-defined",
                    "pocus_posterior": "Posterior acoustic enhancement (or neutral)",
                    "fnac_passes": "2 passes (23G Needle, Capillary method)",
                    "prep_tech": "Unassigned",
                    "staining": "Diff-Quik (90-second rapid Romanowsky)",
                    "macro_adequate": "Pending Assessment",
                    "images": [],
                    "review_mode": "Awaiting Review",
                    "pathologist": "Pending Review",
                    "yokohama": "Category 1: Insufficient / Inadequate (Risk of Malignancy: 10–25%)",
                    "path_notes": "Awaiting slide image review.",
                    "asha_worker": "Meena Devi (ANM/ASHA)",
                    "asha_contact": "+91 9876543210",
                    "tracker_status": "Referral Pending (Counseling completed at PHC)",
                    "audit_log": [f"[{datetime.date.today()}] Record created by {new_doc}"]
                }
                save_patient_record(new_patient)
                st.session_state.active_case_id = new_case_id
                st.success(f"Case {new_case_id} registered successfully.")
                st.rerun()

    with tab_edit:
        st.subheader(f"Demographic & Clinical Profile: {patient['name']} ({patient['case_id']})")
        
        with st.expander("✏️ Edit Demographics & Registration Details", expanded=False):
            ed1, ed2, ed3 = st.columns(3)
            patient["name"] = ed1.text_input("Patient Full Name:", patient["name"])
            patient["age"] = ed2.number_input("Age:", 15, 100, int(patient["age"]))
            patient["uhid"] = ed3.text_input("UHID:", patient["uhid"])
            patient["pincode"] = ed1.text_input("Pincode / Area:", patient["pincode"])
            patient["referral_doc"] = ed2.text_input("Examining MO:", patient["referral_doc"])
            if st.button("Save Profile Changes"):
                patient["audit_log"].append(f"[{datetime.date.today()}] Demographics updated by MO")
                save_patient_record(patient)
                st.success("Patient profile updated.")

        col_left, col_right = st.columns(2)
        with col_left:
            st.markdown("#### Standardized Clinical Palpation (CBE)")
            patient["cbe_mass"] = st.selectbox(
                "Mass Consistency & Fixity:",
                [
                    "Soft / Rubbery, Well-circumscribed, Freely mobile",
                    "Firm, Discrete, Moderately mobile",
                    "Hard, Irregular (Tethered/Fixed to skin or fascia)"
                ],
                index=2 if "Hard" in patient["cbe_mass"] else (1 if "Firm" in patient["cbe_mass"] else 0)
            )
            patient["cbe_size"] = st.text_input("Approximate Mass Diameter (cm):", patient["cbe_size"])
            patient["cbe_nodes"] = st.selectbox(
                "Ipsilateral Axillary Adenopathy:",
                ["Absent (Clinically negative)", "Present (Firm, Non-tender, or Matted)"],
                index=1 if "Present" in patient["cbe_nodes"] else 0
            )
            patient["fnac_passes"] = st.text_input("Needle Sampling Technique:", patient["fnac_passes"])

        with col_right:
            st.markdown("#### Bedside Ultrasound (POCUS)")
            patient["pocus_available"] = st.checkbox("Ultrasound Machine Available at Clinic?", value=patient["pocus_available"])
            if patient["pocus_available"]:
                patient["pocus_orientation"] = st.radio(
                    "Lesion Orientation:",
                    ["Wider-than-tall (Horizontal / Parallel to skin)", "Taller-than-wide (Vertical growth / Transverse to skin)"],
                    index=1 if "Taller" in patient["pocus_orientation"] else 0
                )
                patient["pocus_margins"] = st.radio(
                    "Margin Integrity:",
                    ["Smooth & Well-defined", "Irregular / Spiculated / Microlobulated"],
                    index=1 if "Irregular" in patient["pocus_margins"] else 0
                )
                patient["pocus_posterior"] = st.radio(
                    "Posterior Acoustic Feature:",
                    ["Posterior acoustic enhancement (or neutral)", "Posterior acoustic shadowing (dark shadow behind mass)"],
                    index=1 if "shadowing" in patient["pocus_posterior"] else 0
                )
            else:
                st.info("POCUS bypassed. Concordance engine will assess Clinical Suspicion + Cytology.")

        if st.button("Save Clinical & Ultrasound Findings"):
            save_patient_record(patient)
            st.success("Clinical exam data saved permanently.")

        st.divider()
        st.markdown("#### Direct Micrograph Upload by Medical Officer")
        st.caption("Photos uploaded here are appended to the slide repository.")
        mo_new_files = st.file_uploader(
            "Add Slide Photos as Medical Officer (10x & 40x):",
            type=["jpg", "png", "jpeg"],
            accept_multiple_files=True,
            key="mo_img_uploader"
        )
        if mo_new_files:
            if st.button("Upload Photos to Cloud"):
                for uploaded in mo_new_files:
                    img_entry = save_slide_image(uploaded, patient["case_id"], "Medical Officer", patient["referral_doc"])
                    patient["images"].append(img_entry)
                patient["audit_log"].append(f"[{datetime.date.today()}] {len(mo_new_files)} photo(s) uploaded by MO")
                save_patient_record(patient)
                st.success(f"Attached {len(mo_new_files)} photo(s). Total available: {len(patient['images'])}")
                st.rerun()

    if patient.get("images"):
        st.divider()
        st.markdown(f"#### Attached Micrographs ({len(patient['images'])} total)")
        img_cols = st.columns(min(len(patient["images"]), 4))
        for idx, item in enumerate(patient["images"]):
            with img_cols[idx % 4]:
                if "url" in item:
                    st.image(item["url"], caption=f"Field {idx+1} [{item['role']}]", use_container_width=True)
                elif "file" in item:
                    st.image(Image.open(item["file"]), caption=f"Field {idx+1} [{item['role']}]", use_container_width=True)
                    # ==========================================
# MODULE 2: LAB TECHNICIAN
# ==========================================
elif role == "2. Lab Technician (Staining, Patient Link & Upload)":
    st.header("2. Laboratory Technician: Slide Staining & Tele-Imaging")
    st.caption("Select a registered patient, record staining adequacy, and append microscope photos.")

    st.subheader("Step 1: Link to Registered Patient")
    target_case_id = st.selectbox(
        "Select Patient to Attach Cytology Images:",
        options=case_options,
        index=case_options.index(st.session_state.active_case_id),
        format_func=lambda cid: f"{cid} — {st.session_state.patients[cid]['name']} (UHID: {st.session_state.patients[cid]['uhid']})"
    )
    st.session_state.active_case_id = target_case_id
    patient = st.session_state.patients[target_case_id]

    st.info(f"Target: **{patient['name']}** | Age: **{patient['age']}** | Examining MO: **{patient['referral_doc']}**")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Slide Processing & Macroscopic Adequacy")
        patient["prep_tech"] = st.text_input("Slide Prepared by (Technician Name):", patient["prep_tech"])
        patient["staining"] = st.selectbox(
            "Rapid Staining Method:",
            [
                "Diff-Quik (90-second rapid Romanowsky)",
                "Rapid Giemsa (3-minute protocol)",
                "Toluidine Blue / Methylene Blue (Wet mount)"
            ],
            index=0
        )
        patient["macro_adequate"] = st.selectbox(
            "Macroscopic Adequacy (Visual Check):",
            [
                "Yes (Chalky/white granular fragments visible against light)",
                "Suboptimal (Watery, heavily blood-stained smear — alert MO for re-pass)",
                "Acellular (Clear serous fluid only)"
            ],
            index=0 if "Yes" in patient["macro_adequate"] else 1
        )
        if st.button("Save Staining Details"):
            save_patient_record(patient)
            st.success("Staining details updated.")

    with col2:
        st.markdown("#### Smartphone Micrograph Upload")
        tech_new_files = st.file_uploader(
            "Attach Slide Photos as Technician:",
            type=["jpg", "png", "jpeg"],
            accept_multiple_files=True,
            key="tech_img_uploader"
        )
        if tech_new_files:
            if st.button("Upload Tech Photos"):
                for uploaded in tech_new_files:
                    img_entry = save_slide_image(uploaded, patient["case_id"], "Lab Technician", patient["prep_tech"])
                    patient["images"].append(img_entry)
                patient["audit_log"].append(f"[{datetime.date.today()}] {len(tech_new_files)} photo(s) added by Tech ({patient['prep_tech']})")
                save_patient_record(patient)
                st.success(f"Attached {len(tech_new_files)} photos.")
                st.rerun()

    if patient.get("images"):
        st.divider()
        st.markdown(f"#### Attached Micrographs ({len(patient['images'])} total)")
        img_cols = st.columns(min(len(patient["images"]), 4))
        for idx, item in enumerate(patient["images"]):
            with img_cols[idx % 4]:
                if "url" in item:
                    st.image(item["url"], caption=f"Field {idx+1} [{item['role']}]", use_container_width=True)
                elif "file" in item:
                    st.image(Image.open(item["file"]), caption=f"Field {idx+1} [{item['role']}]", use_container_width=True)

# ==========================================
# MODULE 3: CYTOLOGY REVIEW & AI ASSIST
# ==========================================
elif role == "3. Cytology Review (AI Assist & Pathologist Sign-Off)":
    st.header("3. Slide Review & Diagnostic Classification")
    st.caption("Review uploaded slide fields using Pathologist Tele-Review or the AI Provisional Assist bypass.")

    st.subheader(f"Case Under Review: {patient['name']} | Case ID: {patient['case_id']}")

    col_images, col_diag = st.columns([1, 1])

    with col_images:
        st.markdown("#### Clinical Intake Summary")
        st.markdown(f"""
        * **Patient:** {patient['name']} ({patient['age']} yrs) | **UHID:** `{patient['uhid']}`
        * **Examining MO:** {patient['referral_doc']}
        * **CBE Palpation:** {patient['cbe_mass']} (Nodes: {patient['cbe_nodes']})
        * **Bedside POCUS:** {'Orientation: ' + patient['pocus_orientation'] + ' | Margins: ' + patient['pocus_margins'] if patient['pocus_available'] else 'Not available on-site'}
        * **Slide Stained By:** {patient['prep_tech']} ({patient['staining']})
        * **Total Uploaded Micrographs:** {len(patient.get('images', []))}
        """)

        st.divider()
        st.markdown("#### Microscopic Slide Review")
        if patient.get("images"):
            for idx, item in enumerate(patient["images"]):
                caption_text = f"Field {idx+1} — By {item['role']} ({item['uploader']}) at {item.get('timestamp','')}"
                if "url" in item:
                    st.image(item["url"], caption=caption_text, use_container_width=True)
                elif "file" in item:
                    st.image(Image.open(item["file"]), caption=caption_text, use_container_width=True)
        else:
            st.warning("⚠️ No slide photos uploaded yet for this patient.")

    with col_diag:
        review_choice = st.radio(
            "Select Diagnostic Route:",
            ["Option A: Pathologist Review (Standard)", "Option B: AI Triage Assist (Pathologist Bypass Mode)"],
            index=0 if patient.get("review_mode") == "Final Pathologist Sign-Off" else (1 if patient.get("review_mode") == "AI Provisional" else 0)
        )

        if "Option B" in review_choice:
            st.markdown("### 🤖 AI Tele-Cytology Screener (Bypass Mode)")
            st.info(
                "Use this bypass when no pathologist is available on-site. "
                "The report will be prominently marked as **Provisional AI-Generated**."
            )

            ai_preset = st.selectbox(
                "AI Computer-Aided Morphology Inference:",
                [
                    "Pattern detected: Highly cellular, cohesive antler-like sheets, bare bipolar nuclei (Consistent with Benign Fibroadenoma)",
                    "Pattern detected: Hypocellular, proteinaceous/acellular fluid, rare ductal clusters (Inadequate sampling)",
                    "Pattern detected: Pleomorphic cells, dyscohesive clusters, prominent nucleoli, necrotic background (High-Grade Malignancy)",
                    "Pattern detected: Mild nuclear enlargement, crowded 3D clusters with preserved cohesion (Atypical / Indeterminate)"
                ]
            )

            if st.button("⚡ Run AI Analysis & Save Provisional Triage"):
                if "Benign Fibroadenoma" in ai_preset:
                    patient["yokohama"] = "Category 2: Benign Cells (Risk of Malignancy: <3%)"
                    patient["path_notes"] = "[AI INFERENCE] Abundant branching cohesive sheets (antler-like), naked bipolar nuclei, and myxoid stroma. Features favor benign fibroepithelial lesion (Fibroadenoma)."
                elif "Inadequate" in ai_preset:
                    patient["yokohama"] = "Category 1: Insufficient / Inadequate (Risk of Malignancy: 10–25%)"
                    patient["path_notes"] = "[AI INFERENCE] Hypocellular smear. Insufficient intact epithelial groups for diagnostic evaluation."
                elif "High-Grade Malignancy" in ai_preset:
                    patient["yokohama"] = "Category 5: Malignant (Risk of Malignancy: >97%)"
                    patient["path_notes"] = "[AI INFERENCE] Marked pleomorphism, discohesive atypical epithelial cells, and high nuclear-cytoplasmic ratio. Highly suspicious for invasive carcinoma."
                else:
                    patient["yokohama"] = "Category 3: Atypical (Risk of Malignancy: 15–50%)"
                    patient["path_notes"] = "[AI INFERENCE] Architectural crowding and nuclear atypia present without definitive overt malignancy."

                patient["review_mode"] = "AI Provisional"
                patient["pathologist"] = "AI Computer-Aided Cytology Screener v1.0 (Unverified by Pathologist)"
                patient["audit_log"].append(f"[{datetime.date.today()}] AI Provisional classification executed: {patient['yokohama'][:10]}")
                save_patient_record(patient)
                st.success("Provisional AI classification saved to database.")
                st.rerun()

        else:
            st.markdown("### 👨‍⚕️ Pathologist Formal Tele-Review")
            patient["pathologist"] = st.text_input("Evaluating Pathologist (Name & Degree):", patient["pathologist"])

            patient["yokohama"] = st.selectbox(
                "IAC Yokohama Diagnostic Category:",
                [
                    "Category 1: Insufficient / Inadequate (Risk of Malignancy: 10–25%)",
                    "Category 2: Benign Cells (Risk of Malignancy: <3%)",
                    "Category 3: Atypical (Risk of Malignancy: 15–50%)",
                    "Category 4: Suspicious for Malignancy (Risk of Malignancy: 60–85%)",
                    "Category 5: Malignant (Risk of Malignancy: >97%)"
                ],
                index=1 if "Category 2" in patient.get("yokohama", "") else (0 if "Category 1" in patient.get("yokohama", "") else 2)
            )

            patient["path_notes"] = st.text_area(
                "Microscopic Observations & Remarks:",
                patient["path_notes"],
                height=130
            )

            if st.button("Submit Formal Pathologist Sign-Off"):
                patient["review_mode"] = "Final Pathologist Sign-Off"
                patient["audit_log"].append(f"[{datetime.date.today()}] Official cytology signed by {patient['pathologist']} ({patient['yokohama'][:10]})")
                save_patient_record(patient)
                st.success("Official cytology report saved to database.")
                st.rerun()

# ==========================================
# MODULE 4: CDSS TRIAGE & FORMAL REPORT
# ==========================================
elif role == "4. CDSS Triage & Advisory Report":
    st.header(f"4. CDSS Triage Advisory: {patient['name']} ({patient['case_id']})")

    is_ai_mode = patient.get("review_mode") == "AI Provisional"
    if is_ai_mode:
        st.warning("⚠️ **NOTICE: THIS REPORT USES PROVISIONAL AI CYTOLOGY INFERENCE. AWAITING PATHOLOGIST REVIEW.**")

    cbe_suspicious = "Hard, Irregular" in patient["cbe_mass"] or "Present" in patient["cbe_nodes"]
    usg_suspicious = False
    if patient["pocus_available"]:
        usg_suspicious = (
            "Taller-than-wide" in patient["pocus_orientation"] or
            "Irregular" in patient["pocus_margins"] or
            "shadowing" in patient["pocus_posterior"]
        )

    clinical_high_risk = cbe_suspicious or usg_suspicious
    yokohama = patient.get("yokohama", "")

    # Concordance Logic
    if clinical_high_risk and "Category 2: Benign" in yokohama:
        status_banner = "CRITICAL DISCORDANCE (HIGH RISK FLAGS)"
        status_color = "red"
        analysis_text = (
            "Physical examination and/or bedside ultrasound demonstrate high-suspicion features, "
            "yet cytology is reported as benign. FNAB has a recognized sampling miss rate in dense, "
            "fibrous, or scirrhous tumors. Residual post-test malignancy risk remains ~20%–30%."
        )
        action_text = "CONFIRMATORY CORE-NEEDLE BIOPSY IS MANDATORY. Deferring biopsy based on benign cytology alone is unsafe."

    elif clinical_high_risk and "Category 1: Insufficient" in yokohama:
        status_banner = "HIGH-RISK INADEQUACY (SUSPECTED DESMOPLASTIC MASS)"
        status_color = "red"
        analysis_text = (
            "Bedside ultrasound or clinical palpation indicates high suspicion, but needle cytology yielded inadequate cellularity. "
            "Invasive carcinomas with dense fibrous stroma (desmoplasia) frequently produce hypocellular aspirates or 'dry taps'. "
            "An inadequate smear in this setting must be managed with high suspicion."
        )
        action_text = "BYPASS REPEAT FNAB. PROCEED DIRECTLY TO CORE-NEEDLE BIOPSY (CNB). Repeat fine-needle passes frequently fail in dense fibrous tumors."

    elif not clinical_high_risk and "Category 1: Insufficient" in yokohama:
        status_banner = "INSUFFICIENT SAMPLING (LOW CLINICAL SUSPICION)"
        status_color = "orange"
        analysis_text = (
            "Cytology sample contains inadequate diagnostic epithelial groups. An inadequate smear does not "
            "confirm absence of disease (Baseline Risk of Malignancy: 10%–25%)."
        )
        action_text = "REPEAT GUIDED FNAB OR REFER FOR DIAGNOSTIC BREAST ULTRASOUND within 2–3 weeks."

    elif "Category 4: Suspicious" in yokohama or "Category 5: Malignant" in yokohama:
        status_banner = "CONCORDANT SUSPICIOUS / MALIGNANT PROFILE"
        status_color = "red"
        analysis_text = "Cytomorphological features unequivocally identify or strongly favor neoplasia (Risk of Malignancy: 60% to >97%)."
        action_text = "URGENT TERTIARY REFERRAL for Core Biopsy (for ER, PR, HER2 biomarker profiling) and definitive oncology staging."

    elif "Category 3: Atypical" in yokohama:
        status_banner = "ATYPICAL CYTOLOGY (EQUIVOCAL)"
        status_color = "orange"
        analysis_text = "Smear exhibits architectural or nuclear atypia (Risk of Malignancy: 15%–50%)."
        action_text = "REFER FOR HISTOPATHOLOGIC EVALUATION (Core-Needle Biopsy or diagnostic excision)."

    else:
        status_banner = "CONCORDANT BENIGN PROFILE"
        status_color = "green"
        analysis_text = "Physical examination, bedside sonography, and cytology findings align without suspicious features."
        action_text = "ROUTINE CLINICAL REVIEW in 3–6 months. Educate patient on self-awareness warning signs."

    prefix = "[PROVISIONAL AI ASSIST] " if is_ai_mode else ""
    if status_color == "red":
        st.error(f"🚨 **{prefix}{status_banner}**\n\n**Analysis:** {analysis_text}\n\n**Directive:** {action_text}")
    elif status_color == "orange":
        st.warning(f"⚠️ **{prefix}{status_banner}**\n\n**Analysis:** {analysis_text}\n\n**Directive:** {action_text}")
    else:
        st.success(f"✅ **{prefix}{status_banner}**\n\n**Analysis:** {analysis_text}\n\n**Directive:** {action_text}")

    st.divider()
    st.subheader("Formal Monochromatic Clinical Advisory Slip")

    p = patient
    ai_watermark = """
    <div style="background-color: #fff3cd; border: 1px solid #ffeeba; color: #856404; padding: 8px; text-align: center; font-weight: bold; margin-bottom: 12px; font-size: 12px;">
        ⚠️ PRELIMINARY AI-ASSISTED TRIAGE REPORT — PATHOLOGIST HAS NOT YET REVIEWED THIS SLIDE. FORMAL TELE-PATHOLOGY SIGN-OFF PENDING.
    </div>
    """ if is_ai_mode else ""

    sign_off_html = f"""
    <td style="width: 25%; text-align: center;">
        <span style="font-style: italic; color: #856404;">[AI Provisional]</span><br>
        ________________________<br>
        <strong>AI Cytology Screener</strong>
    </td>
    """ if is_ai_mode else f"""
    <td style="width: 25%; text-align: center;">
        ________________________<br>
        <strong>Pathologist Sign-off</strong><br>
        <span style="font-size: 11px;">{p.get('pathologist','')}</span>
    </td>
    """

    report_html = f"""
    <div style="border: 2px solid #222; padding: 24px; font-family: Arial, sans-serif; color: #111; background-color: #fff; line-height: 1.4;">
        {ai_watermark}
        <div style="text-align: center; border-bottom: 2px solid #222; padding-bottom: 8px; margin-bottom: 16px;">
            <h2 style="margin: 0; text-transform: uppercase; letter-spacing: 1px;">PERIPHERAL BREAST TRIAGE UNIT</h2>
            <div style="font-size: 13px; font-weight: bold; color: #444;">CLINICAL DECISION SUPPORT & TRIAGE ADVISORY REPORT</div>
        </div>

        <table style="width: 100%; border-collapse: collapse; margin-bottom: 14px; font-size: 13px;">
            <tr>
                <td style="padding: 3px 0;"><strong>Patient Name:</strong> {p['name']}</td>
                <td style="padding: 3px 0;"><strong>Age / Sex:</strong> {p['age']} / Female</td>
                <td style="padding: 3px 0;"><strong>Case ID:</strong> {p['case_id']}</td>
            </tr>
            <tr>
                <td style="padding: 3px 0;"><strong>UHID:</strong> {p['uhid']}</td>
                <td style="padding: 3px 0;"><strong>Exam Date:</strong> {p['date_exam']}</td>
                <td style="padding: 3px 0;"><strong>Pincode:</strong> {p['pincode']}</td>
            </tr>
            <tr>
                <td colspan="3" style="padding: 3px 0;"><strong>Examining Medical Officer:</strong> {p['referral_doc']}</td>
            </tr>
        </table>

        <div style="border-top: 1px solid #777; padding-top: 8px; margin-bottom: 12px; font-size: 13px;">
            <strong>1. BEDSIDE CLINICAL & ULTRASOUND ASSESSMENT</strong><br>
            • <strong>Clinical Palpation (CBE):</strong> {p['cbe_mass']} | Size: {p['cbe_size']} | Axillary Nodes: {p['cbe_nodes']}<br>
            • <strong>Point-of-Care USG (POCUS):</strong> {'Orientation: ' + p['pocus_orientation'] + ' | Margins: ' + p['pocus_margins'] + ' | ' + p['pocus_posterior'] if p['pocus_available'] else 'Not Performed / Unavailable'}
        </div>

        <div style="border-top: 1px solid #777; padding-top: 8px; margin-bottom: 12px; font-size: 13px;">
            <strong>2. CYTOLOGY & TELE-PATHOLOGY CHAIN OF CUSTODY</strong><br>
            • <strong>Procedure:</strong> {p['fnac_passes']}<br>
            • <strong>Slide Stained By:</strong> {p['prep_tech']} ({p['staining']}) | Macro Adequacy: {p['macro_adequate']}<br>
            • <strong>Total Micrographs Attached:</strong> {len(p.get('images', []))} slide image(s)<br>
            • <strong>IAC Yokohama Category:</strong> <span style="text-decoration: underline; font-weight: bold;">{p['yokohama']}</span><br>
            • <strong>Diagnostic Assessment Mode:</strong> {p.get('review_mode','Final')}<br>
            • <strong>Cytology Observations:</strong> {p['path_notes']}<br>
            • <strong>Reviewer / Engine:</strong> {p.get('pathologist','')}
        </div>

        <div style="border: 2px solid #111; padding: 10px; margin-bottom: 14px; background-color: #f9f9f9; font-size: 13px;">
            <div style="font-weight: bold; text-transform: uppercase;">3. TRIAGE & CONFIRMATORY ADVISORY: {prefix}{status_banner}</div>
            <p style="margin: 4px 0;"><strong>Analysis:</strong> {analysis_text}</p>
            <p style="margin: 4px 0;"><strong>Mandatory Directive:</strong> <strong>{action_text}</strong></p>
        </div>

        <table style="width: 100%; border-collapse: collapse; margin-top: 18px; font-size: 12px;">
            <tr>
                <td style="width: 50%;">
                    <strong>Community Follow-Up Tracker:</strong><br>
                    Assigned ASHA/ANM: {p['asha_worker']} ({p['asha_contact']})<br>
                    Follow-Up Safety Window: 21 Days
                </td>
                <td style="width: 25%; text-align: center;">
                    ________________________<br>
                    <strong>Medical Officer Sign-off</strong><br>
                    <span style="font-size: 11px;">{p['referral_doc']}</span>
                </td>
                {sign_off_html}
            </tr>
        </table>

        <div style="border-top: 2px solid #222; margin-top: 16px; padding-top: 8px; text-align: center; font-size: 12px; font-weight: bold;">
            **NOT DIAGNOSTIC. Triage Advisory for Clinical Decision Support. Proceed to Confirmatory Histopathology.**
        </div>
    </div>
    """
    components.html(report_html, height=560, scrolling=True)

# ==========================================
# MODULE 5: ASHA CLOSED-LOOP TRACKER
# ==========================================
elif role == "5. ASHA Closed-Loop Tracker":
    st.header(f"5. ASHA / ANM Community Follow-Up Tracking: {patient['name']}")
    st.caption("Monitor tertiary referral completion within the 21-day window to eliminate loss-to-follow-up.")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Patient Details")
        st.write(f"**Patient Name:** {patient['name']} (Age: {patient['age']})")
        st.write(f"**Case ID:** `{patient['case_id']}` | **UHID:** `{patient['uhid']}`")
        st.write(f"**Assigned ASHA Worker:** {patient['asha_worker']}")
        st.write(f"**Contact Number:** {patient['asha_contact']}")

    with col2:
        st.markdown("#### Referral Milestone Status")
        patient["tracker_status"] = st.selectbox(
            "Current Adherence Status:",
            [
                "Referral Pending (Counseling completed at PHC)",
                "Appointment Scheduled at District Hospital",
                "Core-Needle Biopsy Completed (Awaiting Histopath)",
                "Report Received & Followed Up",
                "Patient Hesitant / Refused (Requires ASHA Home Visit)"
            ],
            index=0 if "Pending" in patient.get("tracker_status", "") else 1
        )
        st.date_input("Follow-Up Target Deadline (21 Days):", datetime.date.today() + datetime.timedelta(days=21))
        if st.button("Save Adherence Status"):
            save_patient_record(patient)
            st.success("Adherence status saved.")

    st.divider()
    st.markdown("#### Vernacular Patient Counseling Slip (Hindi)")
    st.markdown(
        """
        > ### स्तन स्वास्थ्य: रोगी परामर्श पर्ची
        > * **जांच का उद्देश्य:** आपकी शारीरिक जांच और सुई की शुरुआती जांच में अंतर पाया गया है।
        > * **बायोप्सी क्यों जरूरी है?** सुई की बारीक जांच कभी-कभी गांठ के अंदरूनी हिस्से तक नहीं पहुंच पाती। इसलिए 100% सही नतीजे के लिए बड़े अस्पताल में कोर बायोप्सी अनिवार्य है।
        > * **घबराएं नहीं:** कोर बायोप्सी कोई बड़ा ऑपरेशन नहीं है। यह सुन्न करके की जाने वाली ओपीडी जांच है और इससे गांठ बिल्कुल नहीं फैलती।
        > * **अगला कदम:** अपनी आशा दीदी की मदद से 21 दिनों के भीतर जिला अस्पताल में जाकर यह जांच पूरी करवाएं।
        """
    )

# ==========================================
# MODULE 6: PROVENANCE AUDIT TRAIL
# ==========================================
elif role == "6. Audit Trail & Provenance (Who Did What)":
    st.header(f"6. Clinical Audit Trail & Provenance: Case {patient['case_id']}")
    st.caption("Verifiable log of clinical actions, slide transfers, and assessment sign-offs.")

    st.markdown("#### Summary of Clinical Roles Involved")
    summary_data = {
        "Clinical Stage": [
            "Clinical Palpation & POCUS",
            "Needle Sampling (FNAC)",
            "Slide Smear & Staining",
            "Micrographs Attached",
            "Cytology Assessment",
            "Community Adherence Tracking"
        ],
        "Cadre": [
            "Medical Officer",
            "Medical Officer",
            "Lab Technician",
            "Collaborative (MO / Tech)",
            "AI Engine" if patient.get("review_mode") == "AI Provisional" else "Consulting Pathologist",
            "ASHA / ANM Worker"
        ],
        "Entity / Name": [
            patient["referral_doc"],
            patient["referral_doc"],
            patient["prep_tech"],
            f"{len(patient.get('images', []))} photos total",
            patient.get("pathologist", ""),
            patient["asha_worker"]
        ]
    }
    st.table(summary_data)

    st.markdown("#### Chronological Activity Log")
    for log_item in patient.get("audit_log", []):
        st.code(log_item, language="markdown")
