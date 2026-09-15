import datetime
import streamlit as st
import streamlit.components.v1 as components
from PIL import Image

st.set_page_config(
    page_title="Breast Triage CDSS",
    page_icon="🩺",
    layout="wide"
)

# --- SESSION STATE INITIALIZATION ---
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
            "image_uploader_role": "Lab Technician",
            "image_uploader_name": "Lab Tech Sarah Khan",
            "tele_images": [],
            "pathologist": "Dr. Priya Sharma, MD Pathology",
            "yokohama": "Category 2: Benign Cells (Risk of Malignancy: <3%)",
            "path_notes": "Abundant naked bipolar nuclei with sheets of cohesive benign ductal epithelial cells. No marked atypia in viewed fields.",
            "asha_worker": "Meena Devi (ANM/ASHA)",
            "asha_contact": "+91 9876543210",
            "tracker_status": "Referral Pending (Counseling completed at PHC)",
            "audit_log": [
                f"[{datetime.date.today()} 09:30] Clinical exam and POCUS performed by Dr. Rajiv Singh, MBBS",
                f"[{datetime.date.today()} 09:45] Slide prepared & stained with Diff-Quik by Lab Tech Sarah Khan"
            ]
        }
    }

if "active_case_id" not in st.session_state:
    st.session_state.active_case_id = "PB-2026-1035"

# --- SIDEBAR NAVIGATION & PATIENT SELECTION ---
st.sidebar.title("🩺 Breast Triage CDSS")
st.sidebar.caption("Evidence-Based Bedside Decision Support")

case_options = list(st.session_state.patients.keys())
selected_case = st.sidebar.selectbox(
    "Active Patient Case:",
    options=case_options,
    index=case_options.index(st.session_state.active_case_id) if st.session_state.active_case_id in case_options else 0
)
st.session_state.active_case_id = selected_case
patient = st.session_state.patients[st.session_state.active_case_id]

st.sidebar.markdown(f"**Selected:** {patient['name']}  \n**UHID:** `{patient['uhid']}`")
st.sidebar.divider()

role = st.sidebar.radio(
    "Workflow Cadre View:",
    [
        "1. Medical Officer (Exam, POCUS & Direct Upload)",
        "2. Lab Technician (Staining, Patient Link & Upload)",
        "3. Accessing Pathologist (Consolidated Tele-Review)",
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
    st.caption("Register patients, record clinical breast exams, POCUS morphology, and optionally upload slide photos directly.")

    with st.expander("➕ Register a New Patient Case"):
        with st.form("new_patient_form"):
            c1, c2, c3 = st.columns(3)
            new_name = c1.text_input("Full Name")
            new_age = c2.number_input("Age", 15, 100, 45)
            new_uhid = c3.text_input("UHID / National ID")
            new_case_id = c1.text_input("Assigned Case ID (Unique)", f"PB-2026-{len(st.session_state.patients)+1001}")
            new_pincode = c2.text_input("Pincode", "248001")
            new_doc = c3.text_input("Doctor Name", "Dr. Rajiv Singh, MBBS")
            submit_new = st.form_submit_button("Create Patient Record")

            if submit_new and new_case_id:
                st.session_state.patients[new_case_id] = {
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
                    "image_uploader_role": "None",
                    "image_uploader_name": "None",
                    "tele_images": [],
                    "pathologist": "Unassigned",
                    "yokohama": "Category 1: Insufficient / Inadequate (Risk of Malignancy: 10–25%)",
                    "path_notes": "Awaiting slide image review.",
                    "asha_worker": "Meena Devi (ANM/ASHA)",
                    "asha_contact": "+91 9876543210",
                    "tracker_status": "Referral Pending (Counseling completed at PHC)",
                    "audit_log": [f"[{datetime.date.today()}] Record created by {new_doc}"]
                }
                st.session_state.active_case_id = new_case_id
                st.success(f"Case {new_case_id} created successfully.")
                st.rerun()

    st.subheader(f"Editing Exam Record: {patient['name']} ({patient['case_id']})")
    
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
            index=2 if "Hard" in patient["cbe_mass"] else 1
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
                "Posterior Feature:",
                ["Posterior acoustic enhancement (or neutral)", "Posterior acoustic shadowing (dark shadow behind mass)"],
                index=1 if "shadowing" in patient["pocus_posterior"] else 0
            )
        else:
            st.info("POCUS bypassed. Concordance engine will assess Clinical Suspicion + Cytology.")

    st.divider()
    st.markdown("#### Optional Direct Micrograph Upload by Medical Officer")
    st.caption("Use this if the Medical Officer processes the microscope slide directly.")
    mo_direct_upload = st.file_uploader(
        "Upload Slide Photos directly as Medical Officer (10x Overview & 40x Nuclear Detail):",
        type=["jpg", "png", "jpeg"],
        accept_multiple_files=True,
        key="mo_uploader"
    )
    if mo_direct_upload:
        patient["tele_images"] = mo_direct_upload
        patient["image_uploader_role"] = "Medical Officer"
        patient["image_uploader_name"] = patient["referral_doc"]
        log_entry = f"[{datetime.date.today()}] {len(mo_direct_upload)} slide image(s) uploaded directly by MO ({patient['referral_doc']})"
        if log_entry not in patient["audit_log"]:
            patient["audit_log"].append(log_entry)
        st.success(f"Attached {len(mo_direct_upload)} image(s) to {patient['case_id']} as Medical Officer.")

# ==========================================
# MODULE 2: LAB TECHNICIAN
# ==========================================
elif role == "2. Lab Technician (Staining, Patient Link & Upload)":
    st.header("2. Laboratory Technician: Slide Staining & Tele-Imaging")
    st.caption("Select an existing patient registered by the MO to link the prepared slide and smartphone micrographs.")

    st.subheader("Step 1: Link to Registered Patient")
    target_case_id = st.selectbox(
        "Select Patient to Attach Cytology Findings:",
        options=case_options,
        index=case_options.index(st.session_state.active_case_id),
        format_func=lambda cid: f"{cid} — {st.session_state.patients[cid]['name']} (UHID: {st.session_state.patients[cid]['uhid']})"
    )
    st.session_state.active_case_id = target_case_id
    patient = st.session_state.patients[target_case_id]

    st.info(f"Target Patient: **{patient['name']}** | Age: **{patient['age']}** | Examining MO: **{patient['referral_doc']}**")

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
            "Macroscopic Adequacy (Visual Check on Feather Edge):",
            [
                "Yes (Chalky/white granular fragments visible against light)",
                "Suboptimal (Watery, heavily blood-stained smear — alert MO for re-pass)",
                "Acellular (Clear serous fluid only)"
            ],
            index=0 if "Yes" in patient["macro_adequate"] else 1
        )

    with col2:
        st.markdown("#### Smartphone Photomicrograph Upload")
        st.caption("Attach photos captured through the microscope eyepiece adapter (10x and 40x).")
        tech_uploads = st.file_uploader(
            f"Attach Slide Photos to Case {patient['case_id']}:",
            type=["jpg", "png", "jpeg"],
            accept_multiple_files=True,
            key="tech_uploader"
        )
        if tech_uploads:
            patient["tele_images"] = tech_uploads
            patient["image_uploader_role"] = "Lab Technician"
            patient["image_uploader_name"] = patient["prep_tech"]
            log_entry = f"[{datetime.date.today()}] {len(tech_uploads)} slide image(s) uploaded by Tech ({patient['prep_tech']})"
            if log_entry not in patient["audit_log"]:
                patient["audit_log"].append(log_entry)
            st.success(f"Attached {len(tech_uploads)} image(s) to Case {patient['case_id']}.")

    if patient["tele_images"]:
        st.divider()
        st.markdown(f"#### Micrographs Attached to Case `{patient['case_id']}` (Uploaded by {patient['image_uploader_role']}: {patient['image_uploader_name']})")
        cols = st.columns(min(len(patient["tele_images"]), 4))
        for idx, img_file in enumerate(patient["tele_images"]):
            with cols[idx % 4]:
                st.image(Image.open(img_file), caption=f"Field {idx+1}", use_container_width=True)

# ==========================================
# MODULE 3: PATHOLOGIST
# ==========================================
elif role == "3. Accessing Pathologist (Consolidated Tele-Review)":
    st.header("3. Accessing Pathologist: Consolidated Tele-Review")
    st.caption("Examine patient clinical staging, review uploaded micrographs, and categorize using the IAC Yokohama System.")

    st.subheader(f"Case Under Review: {patient['name']} | Case ID: {patient['case_id']}")

    col_summary, col_review = st.columns([1, 1])

    with col_summary:
        st.markdown("#### Consolidated Clinical & Slide Intake")
        st.markdown(f"""
        * **Patient:** {patient['name']} ({patient['age']} yrs) | **UHID:** `{patient['uhid']}`
        * **Examining Medical Officer:** {patient['referral_doc']}
        * **Clinical Palpation (CBE):** {patient['cbe_mass']} (Size: {patient['cbe_size']}, Nodes: {patient['cbe_nodes']})
        * **Bedside Ultrasound (POCUS):** {'Orientation: ' + patient['pocus_orientation'] + ' | Margins: ' + patient['pocus_margins'] if patient['pocus_available'] else 'Not available on-site'}
        * **Slide Prepared By:** {patient['prep_tech']} ({patient['staining']})
        * **Slide Image Source:** **{patient['image_uploader_role']}** ({patient['image_uploader_name']})
        """)

        st.divider()
        st.markdown("#### Microscopic Review Fields")
        if patient["tele_images"]:
            st.info(f"Showing {len(patient['tele_images'])} digitized field(s) uploaded by {patient['image_uploader_role']} ({patient['image_uploader_name']}):")
            for idx, img in enumerate(patient["tele_images"]):
                st.image(Image.open(img), caption=f"Field {idx+1}", use_container_width=True)
        else:
            st.warning("⚠️ No photomicrographs have been uploaded for this patient yet.")

    with col_review:
        st.markdown("#### Standardized Cytology Classification")
        patient["pathologist"] = st.text_input("Evaluating Pathologist (Name & Degree):", patient["pathologist"])

        patient["yokohama"] = st.selectbox(
            "IAC Yokohama Category:",
            [
                "Category 1: Insufficient / Inadequate (Risk of Malignancy: 10–25%)",
                "Category 2: Benign Cells (Risk of Malignancy: <3%)",
                "Category 3: Atypical (Risk of Malignancy: 15–50%)",
                "Category 4: Suspicious for Malignancy (Risk of Malignancy: 60–85%)",
                "Category 5: Malignant (Risk of Malignancy: >97%)"
            ],
            index=1 if "Category 2" in patient["yokohama"] else 0
        )

        patient["path_notes"] = st.text_area(
            "Microscopic Description & Cell Morphology Observations:",
            patient["path_notes"],
            height=140
        )

        if st.button("Submit Official Cytology Report"):
            log_entry = f"[{datetime.date.today()}] Cytology finalized as {patient['yokohama'][:10]} by {patient['pathologist']}"
            if log_entry not in patient["audit_log"]:
                patient["audit_log"].append(log_entry)
            st.success(f"Report signed and saved for Case {patient['case_id']}.")

# ==========================================
# MODULE 4: CDSS TRIAGE & FORMAL REPORT
# ==========================================
elif role == "4. CDSS Triage & Advisory Report":
    st.header(f"4. CDSS Triage Advisory: {patient['name']} ({patient['case_id']})")

    cbe_suspicious = "Hard, Irregular" in patient["cbe_mass"] or "Present" in patient["cbe_nodes"]
    usg_suspicious = False
    if patient["pocus_available"]:
        usg_suspicious = (
            "Taller-than-wide" in patient["pocus_orientation"] or
            "Irregular" in patient["pocus_margins"] or
            "shadowing" in patient["pocus_posterior"]
        )

    clinical_high_risk = cbe_suspicious or usg_suspicious
    yokohama = patient["yokohama"]

    if clinical_high_risk and "Category 2: Benign" in yokohama:
        status_banner = "CRITICAL DISCORDANCE (HIGH RISK FLAGS)"
        status_color = "red"
        analysis_text = (
            "Physical examination and/or bedside ultrasound demonstrate high-suspicion features, "
            "yet fine-needle aspiration cytology is reported as benign. FNAB has a recognized false-negative "
            "rate due to geographic sampling misses in dense or scirrhous tumors. "
            "Residual post-test malignancy risk remains approximately ~20%–30%."
        )
        action_text = "CONFIRMATORY CORE-NEEDLE BIOPSY IS MANDATORY. Deferring biopsy or reassuring the patient is unsafe."
    elif "Category 1: Insufficient" in yokohama:
        status_banner = "INSUFFICIENT SAMPLING (INDETERMINATE)"
        status_color = "orange"
        analysis_text = (
            "Cytology sample contains inadequate diagnostic epithelial groups. An inadequate smear does not "
            "indicate an absence of malignancy (Baseline Risk of Malignancy: 10%–25%)."
        )
        action_text = "REPEAT GUIDED FNAB OR PROCEED DIRECTLY TO CORE BIOPSY based on clinical suspicion."
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
        action_text = "ROUTINE CLINICAL REVIEW in 3–6 months. Educate patient on warning signs."

    if status_color == "red":
        st.error(f"🚨 **{status_banner}**\n\n**Analysis:** {analysis_text}\n\n**Directive:** {action_text}")
    elif status_color == "orange":
        st.warning(f"⚠️ **{status_banner}**\n\n**Analysis:** {analysis_text}\n\n**Directive:** {action_text}")
    else:
        st.success(f"✅ **{status_banner}**\n\n**Analysis:** {analysis_text}\n\n**Directive:** {action_text}")

    st.divider()
    st.subheader("Formal Monochromatic Clinical Advisory Slip")
    st.caption("Standardized print-ready report detailing complete chain of custody.")

    p = patient
    report_html = f"""
    <div style="border: 2px solid #222; padding: 24px; font-family: Arial, sans-serif; color: #111; background-color: #fff; line-heigh: 1.4;">
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
            • <strong>Micrograph Captured & Uploaded By:</strong> {p['image_uploader_role']} — {p['image_uploader_name']} ({len(p['tele_images'])} photos)<br>
            • <strong>IAC Yokohama Category:</strong> <span style="text-decoration: underline; font-weight: bold;">{p['yokohama']}</span><br>
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
                    Follow-Up Safety Window: 21 Days
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
    components.html(report_html, height=540, scrolling=True)

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
            index=0 if "Pending" in patient["tracker_status"] else 1
        )
        st.date_input("Follow-Up Target Deadline (21 Days):", datetime.date.today() + datetime.timedelta(days=21))

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
    st.caption("Verifiable log of every clinical action, slide transfer, and assessment sign-off.")

    st.markdown("#### Summary of Clinical Roles Involved")
    summary_data = {
        "Action": [
            "Clinical Palpation & POCUS",
            "Needle Sampling (FNAC)",
            "Slide Smear & Staining",
            "Photomicrograph Upload",
            "Yokohama Cytology Assessment",
            "Community Adherence Tracking"
        ],
        "Cadre": [
            "Medical Officer",
            "Medical Officer",
            "Lab Technician",
            patient["image_uploader_role"],
            "Consulting Pathologist",
            "ASHA / ANM Worker"
        ],
        "Individual Responsible": [
            patient["referral_doc"],
            patient["referral_doc"],
            patient["prep_tech"],
            patient["image_uploader_name"],
            patient["pathologist"],
            patient["asha_worker"]
        ]
    }
    st.table(summary_data)

    st.markdown("#### Chronological Activity Log")
    for log_item in patient["audit_log"]:
        st.code(log_item, language="markdown")


