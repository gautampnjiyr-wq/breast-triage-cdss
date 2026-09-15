import datetime
import streamlit as st
from PIL import Image

st.set_page_config(
    page_title="Breast Triage CDSS",
    page_icon="🩺",
    layout="wide"
)

# --- SESSION STATE INITIALIZATION ---
if "patient_data" not in st.session_state:
    st.session_state.patient_data = {
        "name": "Sunita Sharma",
        "age": 48,
        "uhid": "PB10003501",
        "case_id": "PB-2026-1035",
        "date_exam": datetime.date.today(),
        "referral_doc": "Dr. Rajiv Singh, MBBS",
        "pincode": "248001",
        "asha_worker": "Meena Devi (ANM/ASHA)",
        "asha_contact": "+91 9876543210",
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
        "tele_images": [],
        "pathologist": "Dr. Priya Sharma, MD Pathology",
        "yokohama": "Category 2: Benign Cells (Risk of Malignancy: <3%)",
        "path_notes": "Abundant naked bipolar nuclei with sheets of cohesive benign ductal epithelial cells. No marked atypia in viewed fields.",
        "tracker_status": "Referral Pending (Counseling completed at PHC)"
    }

# --- SIDEBAR ROLE ROUTER ---
st.sidebar.title("🩺 Breast Triage CDSS")
st.sidebar.caption("Evidence-Based Clinical Decision Support System")

role = st.sidebar.radio(
    "Select Workflow Cadre:",
    [
        "1. Medical Officer (Exam & Bedside POCUS)",
        "2. Lab Technician (Staining & Microscopy)",
        "3. Accessing Pathologist (Tele-Review)",
        "4. CDSS Triage & Advisory Report",
        "5. ASHA Closed-Loop Tracker"
    ]
)

st.sidebar.divider()
st.sidebar.info(
    "**Operating Protocol:** Clinical examination and needle sampling must be executed by a registered Medical Officer. "
    "Technicians manage slide preparation, staining, and tele-cytology imaging."
)

# ==========================================
# MODULE 1: MEDICAL OFFICER
# ==========================================
if role == "1. Medical Officer (Exam & Bedside POCUS)":
    st.header("1. Medical Officer: Clinical Examination & Bedside Staging")
    st.caption("Document patient demographics, standardized clinical palpation, and bedside ultrasound morphology.")

    with st.expander("Patient Demographics & Registration", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.session_state.patient_data["name"] = st.text_input("Patient Name", st.session_state.patient_data["name"])
            st.session_state.patient_data["age"] = st.number_input("Age (Years)", 15, 100, int(st.session_state.patient_data["age"]))
        with col2:
            st.session_state.patient_data["uhid"] = st.text_input("UHID / National ID", st.session_state.patient_data["uhid"])
            st.session_state.patient_data["case_id"] = st.text_input("Case ID", st.session_state.patient_data["case_id"])
        with col3:
            st.session_state.patient_data["referral_doc"] = st.text_input("Examining MO (Name/Degree)", st.session_state.patient_data["referral_doc"])
            st.session_state.patient_data["pincode"] = st.text_input("Area Pincode", st.session_state.patient_data["pincode"])

    col_left, col_right = st.columns(2)
    with col_left:
        st.subheader("Standardized Clinical Breast Exam (CBE)")
        st.session_state.patient_data["cbe_mass"] = st.selectbox(
            "Palpatory Consistency & Fixity:",
            [
                "Soft / Rubbery, Well-circumscribed, Freely mobile",
                "Firm, Discrete, Moderately mobile",
                "Hard, Irregular (Tethered/Fixed to skin or fascia)"
            ],
            index=2
        )
        st.session_state.patient_data["cbe_size"] = st.text_input("Approximate Mass Size (cm)", st.session_state.patient_data["cbe_size"])
        st.session_state.patient_data["cbe_nodes"] = st.selectbox(
            "Ipsilateral Axillary Lymphadenopathy:",
            ["Absent (Clinically negative)", "Present (Firm, Non-tender, or Matted)"],
            index=1
        )
        st.session_state.patient_data["fnac_passes"] = st.text_input(
            "Needle Sampling Technique:",
            st.session_state.patient_data["fnac_passes"]
        )

    with col_right:
        st.subheader("Point-of-Care Ultrasound (POCUS)")
        pocus_on = st.checkbox("Basic Ultrasound Available On-Site?", value=st.session_state.patient_data["pocus_available"])
        st.session_state.patient_data["pocus_available"] = pocus_on

        if pocus_on:
            st.session_state.patient_data["pocus_orientation"] = st.radio(
                "Lesion Orientation:",
                ["Wider-than-tall (Horizontal / Parallel to skin)", "Taller-than-wide (Vertical growth / Transverse to skin)"],
                index=1
            )
            st.session_state.patient_data["pocus_margins"] = st.radio(
                "Margin Integrity:",
                ["Smooth & Well-defined", "Irregular / Spiculated / Microlobulated"],
                index=1
            )
            st.session_state.patient_data["pocus_posterior"] = st.radio(
                "Posterior Acoustic Feature:",
                ["Posterior acoustic enhancement (or neutral)", "Posterior acoustic shadowing (dark shadow behind mass)"],
                index=1
            )
        else:
            st.info("Ultrasound bypassed. Triage engine will evaluate Clinical-Cytological concordance only.")

    st.success("Medical Officer clinical findings recorded.")

# ==========================================
# MODULE 2: LAB TECHNICIAN
# ==========================================
elif role == "2. Lab Technician (Staining & Microscopy)":
    st.header("2. Laboratory Technician: Smear, Staining & Tele-Imaging")
    st.caption("Record rapid slide preparation, macroscopic adequacy, and smartphone photomicrographs.")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Rapid Bedside Slide Processing")
        st.session_state.patient_data["prep_tech"] = st.text_input(
            "Slide Prepared by (Technician Name):",
            st.session_state.patient_data["prep_tech"]
        )
        st.session_state.patient_data["staining"] = st.selectbox(
            "Rapid Staining Protocol Used:",
            [
                "Diff-Quik (90-second rapid Romanowsky)",
                "Rapid Giemsa (3-minute protocol)",
                "Methylene Blue / Toluidine Blue (Instant adequacy wet-mount)"
            ]
        )
        st.session_state.patient_data["macro_adequate"] = st.selectbox(
            "Macroscopic Adequacy (Visual Check on Slide):",
            [
                "Yes (Chalky/white granular fragments visible against light)",
                "Suboptimal (Watery, heavily blood-stained smear — re-pass advised)",
                "Acellular (Clear serous fluid only)"
            ]
        )

    with col2:
        st.subheader("Tele-Cytology Capture (Smartphone Mount)")
        st.markdown(
            """
            * Mount universal clamp onto microscope eyepiece.
            * Set camera to **1.5x zoom** to remove vignetting; lock focus.
            * Capture at least one 10x overview and one 40x nuclear detail field.
            """
        )
        uploaded_files = st.file_uploader(
            "Upload Slide Images (10x Overview & 40x Nuclear Detail):",
            type=["jpg", "png", "jpeg"],
            accept_multiple_files=True
        )
        if uploaded_files:
            st.session_state.patient_data["tele_images"] = uploaded_files
            st.success(f"{len(uploaded_files)} slide photo(s) attached successfully.")

    if st.session_state.patient_data["tele_images"]:
        st.divider()
        st.subheader("Attached Micrographs")
        img_cols = st.columns(min(len(st.session_state.patient_data["tele_images"]), 4))
        for idx, img_file in enumerate(st.session_state.patient_data["tele_images"]):
            with img_cols[idx % 4]:
                image = Image.open(img_file)
                st.image(image, caption=f"Field {idx+1}", use_container_width=True)

# ==========================================
# MODULE 3: PATHOLOGIST
# ==========================================
elif role == "3. Accessing Pathologist (Tele-Review)":
    st.header("3. Accessing Pathologist: Cytology Assessment")
    st.caption("Review digitized fields remotely and categorize using the IAC Yokohama System.")

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("Slide Field Review")
        if st.session_state.patient_data["tele_images"]:
            for idx, img_file in enumerate(st.session_state.patient_data["tele_images"]):
                image = Image.open(img_file)
                st.image(image, caption=f"Photomicrograph {idx+1}", use_container_width=True)
        else:
            st.warning("No tele-cytology images uploaded yet. Technicians can attach files in Module 2.")

    with col2:
        st.subheader("Standardized Diagnostic Classification")
        st.session_state.patient_data["pathologist"] = st.text_input(
            "Accessing Pathologist (Name & Degree):",
            st.session_state.patient_data["pathologist"]
        )

        st.session_state.patient_data["yokohama"] = st.selectbox(
            "IAC Yokohama Diagnostic Category:",
            [
                "Category 1: Insufficient / Inadequate (Risk of Malignancy: 10–25%)",
                "Category 2: Benign Cells (Risk of Malignancy: <3%)",
                "Category 3: Atypical (Risk of Malignancy: 15–50%)",
                "Category 4: Suspicious for Malignancy (Risk of Malignancy: 60–85%)",
                "Category 5: Malignant (Risk of Malignancy: >97%)"
            ],
            index=1
        )

        st.session_state.patient_data["path_notes"] = st.text_area(
            "Microscopic Observations / Remarks:",
            st.session_state.patient_data["path_notes"],
            height=120
        )
        st.success("Pathologist review registered.")

# ==========================================
# MODULE 4: CDSS TRIAGE & FORMAL REPORT
# ==========================================
elif role == "4. CDSS Triage & Advisory Report":
    st.header("4. Clinical Decision Support System (CDSS) Advisory")

    cbe_suspicious = (
        "Hard, Irregular" in st.session_state.patient_data["cbe_mass"] or 
        "Present" in st.session_state.patient_data["cbe_nodes"]
    )
    
    usg_suspicious = False
    if st.session_state.patient_data["pocus_available"]:
        usg_suspicious = (
            "Taller-than-wide" in st.session_state.patient_data["pocus_orientation"] or
            "Irregular" in st.session_state.patient_data["pocus_margins"] or
            "shadowing" in st.session_state.patient_data["pocus_posterior"]
        )

    clinical_high_risk = cbe_suspicious or usg_suspicious
    yokohama = st.session_state.patient_data["yokohama"]

    # Concordance Engine Logic
    if clinical_high_risk and "Category 2: Benign" in yokohama:
        status_banner = "CRITICAL DISCORDANCE (HIGH RISK FLAGS)"
        status_color = "red"
        analysis_text = (
            "Physical examination and/or bedside ultrasound show high-suspicion features, "
            "yet fine-needle aspiration cytology is reported as benign. FNAB has a recognized false-negative "
            "rate due to geographic sampling misses in dense or scirrhous tumors. "
            "Based on Bayesian pre-test probability, residual malignancy risk remains significant (~20%–30%)."
        )
        action_text = "CONFIRMATORY CORE-NEEDLE BIOPSY IS MANDATORY. Deferring biopsy or reassuring the patient as disease-free is clinically unsafe."
    elif "Category 1: Insufficient" in yokohama:
        status_banner = "INSUFFICIENT SAMPLING (INDETERMINATE)"
        status_color = "orange"
        analysis_text = (
            "Cytology sample contains inadequate diagnostic epithelial groups. An inadequate smear does not "
            "indicate an absence of malignancy. Baseline risk of malignancy remains 10%–25%."
        )
        action_text = "REPEAT GUIDED FNAB OR PROCEED DIRECTLY TO CORE BIOPSY based on clinical suspicion."
    elif "Category 4: Suspicious" in yokohama or "Category 5: Malignant" in yokohama:
        status_banner = "CONCORDANT SUSPICIOUS / MALIGNANT PROFILE"
        status_color = "red"
        analysis_text = (
            "Cytomorphological features unequivocally identify or strongly favor neoplasia. "
            "Risk of malignancy is 60% to >97%."
        )
        action_text = "URGENT TERTIARY REFERRAL for Core Biopsy (for ER, PR, HER2 biomarker profiling) and definitive oncology staging."
    elif "Category 3: Atypical" in yokohama:
        status_banner = "ATYPICAL CYTOLOGY (EQUIVOCAL)"
        status_color = "orange"
        analysis_text = "Smear exhibits architectural or nuclear atypia. Risk of malignancy is 15%–50%."
        action_text = "REFER FOR HISTOPATHOLOGIC EVALUATION (Core-Needle Biopsy or diagnostic excision)."
    else:
        status_banner = "CONCORDANT BENIGN PROFILE"
        status_color = "green"
        analysis_text = "Physical examination, bedside sonography, and cytology findings align without suspicious features."
        action_text = "ROUTINE CLINICAL REVIEW in 3–6 months. Educate patient on self-awareness warning signs."

    if status_color == "red":
        st.error(f"🚨 **{status_banner}**\n\n**Analysis:** {analysis_text}\n\n**Directive:** {action_text}")
    elif status_color == "orange":
        st.warning(f"⚠️ **{status_banner}**\n\n**Analysis:** {analysis_text}\n\n**Directive:** {action_text}")
    else:
        st.success(f"✅ **{status_banner}**\n\n**Analysis:** {analysis_text}\n\n**Directive:** {action_text}")

    st.divider()
    st.subheader("Formal Monochromatic Clinical Advisory Slip")
    st.caption("Standardized print-ready report for district hospital referral packets and medical records.")

    p = st.session_state.patient_data
    report_html = f"""
    <div style="border: 2px solid #222; padding: 24px; font-family: Arial, sans-serif; color: #111; background-color: #fff; line-height: 1.4;">
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
                <td style="padding: 3px 0;"><strong>Date:</strong> {p['date_exam']}</td>
                <td style="padding: 3px 0;"><strong>Pincode:</strong> {p['pincode']}</td>
            </tr>
            <tr>
                <td colspan="3" style="padding: 3px 0;"><strong>Referring Medical Officer:</strong> {p['referral_doc']}</td>
            </tr>
        </table>

        <div style="border-top: 1px solid #777; padding-top: 8px; margin-bottom: 12px; font-size: 13px;">
            <strong>1. BEDSIDE CLINICAL & ULTRASOUND ASSESSMENT</strong><br>
            • <strong>Clinical Palpation (CBE):</strong> {p['cbe_mass']} | Size: {p['cbe_size']} | Axillary Nodes: {p['cbe_nodes']}<br>
            • <strong>Point-of-Care USG (POCUS):</strong> {'Orientation: ' + p['pocus_orientation'] + ' | Margins: ' + p['pocus_margins'] + ' | ' + p['pocus_posterior'] if p['pocus_available'] else 'Not Performed / Unavailable'}
        </div>

        <div style="border-top: 1px solid #777; padding-top: 8px; margin-bottom: 12px; font-size: 13px;">
            <strong>2. CYTOLOGY REPORT (IAC YOKOHAMA CLASSIFICATION)</strong><br>
            • <strong>Procedure:</strong> {p['fnac_passes']} | Prepared by: {p['prep_tech']}<br>
            • <strong>Staining:</strong> {p['staining']} | Macro Adequacy: {p['macro_adequate']}<br>
            • <strong>Cytology Category:</strong> <span style="text-decoration: underline; font-weight: bold;">{p['yokohama']}</span><br>
            • <strong>Pathologist Observations:</strong> {p['path_notes']}<br>
            • <strong>Evaluating Pathologist:</strong> {p['pathologist']}
        </div>

        <div style="border: 2px solid #111; padding: 10px; margin-bottom: 14px; background-color: #f9f9f9; font-size: 13px;">
            <div style="font-weight: bold; text-transform: uppercase;">3. TRIAGE & CONFIRMATORY ADVISORY: {status_banner}</div>
            <p style="margin: 4px 0;"><strong>Analysis:</strong> {analysis_text}</p>
            <p style="margin: 4px 0;"><strong>Mandatory Directive:</strong> <strong>{action_text}</strong></p>
        </div>

        <table style="width: 100%; border-collapse: collapse; margin-top: 18px; font-size: 12px;">
            <tr>
                <td style="width: 50%;">
                    <strong>Community Follow-Up Tracker:</strong><br>
                    Assigned ASHA/ANM: {p['asha_worker']} ({p['asha_contact']})<br>
                    Follow-Up Window: 21 Days
                </td>
                <td style="width: 25%; text-align: center;">
                    ________________________<br>
                    <strong>Medical Officer Sign-off</strong>
                </td>
                <td style="width: 25%; text-align: center;">
                    ________________________<br>
                    <strong>Pathologist Sign-off</strong>
                </td>
            </tr>
        </table>

        <div style="border-top: 2px solid #222; margin-top: 16px; padding-top: 8px; text-align: center; font-size: 12px; font-weight: bold;">
            **NOT DIAGNOSTIC. Triage Advisory for Clinical Decision Support. Proceed to Confirmatory Histopathology.**
        </div>
    </div>
    """
    st.components.v1.html(report_html, height=520, scrolling=True)

# ==========================================
# MODULE 5: ASHA CLOSED-LOOP TRACKER
# ==========================================
elif role == "5. ASHA Closed-Loop Tracker":
    st.header("5. ASHA / ANM Community Follow-Up Tracking")
    st.caption("Prevent diagnostic dropout and monitor tertiary referral completion within the 21-day safety window.")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Case Identification")
        st.write(f"**Patient:** {st.session_state.patient_data['name']} (Age: {st.session_state.patient_data['age']})")
        st.write(f"**Case ID:** {st.session_state.patient_data['case_id']} | UHID: {st.session_state.patient_data['uhid']}")
        st.write(f"**Assigned ASHA Worker:** {st.session_state.patient_data['asha_worker']}")
        st.write(f"**Contact:** {st.session_state.patient_data['asha_contact']}")

    with col2:
        st.subheader("Referral Completion Status")
        st.session_state.patient_data["tracker_status"] = st.selectbox(
            "Current Patient Status:",
            [
                "Referral Pending (Counseling completed at PHC)",
                "Appointment Scheduled at District Hospital",
                "Core-Needle Biopsy Completed (Awaiting Histopath)",
                "Report Received & Followed Up",
                "Patient Hesitant / Refused (Requires ASHA Home Visit)"
            ],
            index=0
        )
        st.date_input("Follow-Up Target Date (21 Days):", datetime.date.today() + datetime.timedelta(days=21))

    st.divider()
    st.subheader("Vernacular Patient Counseling Slip (Hindi)")
    st.markdown("Display or print this guidance directly for the patient and family:")

    vernacular_box = """
    > ### स्तन स्वास्थ्य: रोगी परामर्श पर्ची
    > * **जांच का उद्देश्य:** आपकी शारीरिक जांच और सुई की शुरुआती जांच में अंतर पाया गया है।
    > * **बायोप्सी क्यों जरूरी है?** सुई की बारीक जांच कभी-कभी गांठ के अंदरूनी हिस्से तक नहीं पहुंच पाती। इसलिए 100% सही नतीजे के लिए बड़े अस्पताल में कोर बायोप्सी अनिवार्य है।
    > * **घबराएं नहीं:** कोर बायोप्सी कोई बड़ा ऑपरेशन नहीं है। यह सुन्न करके की जाने वाली ओपीडी जांच है और इससे गांठ बिल्कुल नहीं फैलती।
    > * **अगला कदम:** अपनी आशा दीदी की मदद से 21 दिनों के भीतर जिला अस्पताल में जाकर यह जांच पूरी करवाएं।
    """
    st.markdown(vernacular_box)
