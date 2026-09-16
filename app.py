import datetime
import uuid
import urllib.parse
import json
import requests
import streamlit as st
import streamlit.components.v1 as components
from PIL import Image
import numpy as np
import cv2

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

# Database Fetch & Persistence Helpers
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
                    row["asha_area"] = row.get("asha_area") or ""
                    row["asha_contact"] = row.get("asha_contact") or ""
                    row["cbe_notes"] = row.get("cbe_notes") or ""
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
                "cbe_notes": "Firm irregular retroareolar mass with mild skin tethering.",
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
                "path_notes": "Abundant naked bipolar nuclei with sheets of cohesive benign ductal epithelial cells.",
                "asha_worker": "Meena Devi",
                "asha_contact": "9876543210",
                "asha_area": "Sub-Center Raipur, Sector 4",
                "tracker_status": "Referral Pending (Counseling completed at PHC)",
                "audit_log": [f"[{datetime.date.today()} 09:30] Registered & Examined by Dr. Rajiv Singh, MBBS"]
            }
        }
    return st.session_state.patients

def save_patient_record(patient_dict):
    if HAS_SUPABASE:
        try:
            payload = patient_dict.copy()
            if isinstance(payload.get("date_exam"), (datetime.date, datetime.datetime)):
                payload["date_exam"] = payload["date_exam"].isoformat()
            supabase.table("patients").upsert(payload).execute()
        except Exception as e:
            err_msg = str(e)
            if any(col in err_msg for col in ["cbe_notes", "tech_notes", "asha_notes", "mo_contact", "pathologist_phone"]):
                try:
                    safe_payload = payload.copy()
                    for col in ["cbe_notes", "tech_notes", "asha_notes", "mo_contact", "pathologist_phone"]:
                        safe_payload.pop(col, None)
                    supabase.table("patients").upsert(safe_payload).execute()
                except Exception:
                    st.error(f"Error saving to cloud database: {e}")
            else:
                st.error(f"Error saving to cloud database: {e}")
    st.session_state.patients[patient_dict["case_id"]] = patient_dict

# Sync Active Database State
st.session_state.patients = fetch_patient_registry()

# =========================================================================
# STANDALONE PATIENT REPORT PORTAL (INTERCEPT VIA ?view=report)
# =========================================================================
params = st.query_params
if params.get("view") == "report":
    st.markdown("""
        <style>
            [data-testid="stSidebar"] { display: none !important; }
            #MainMenu { visibility: hidden !important; }
            header { visibility: hidden !important; }
            footer { visibility: hidden !important; }
            .block-container { padding: 1rem 1rem !important; max-width: 900px !important; margin: auto !important; }
        </style>
    """, unsafe_allow_html=True)

    cid = params.get("case_id")
    p = st.session_state.patients.get(cid)
    
    if not p:
        st.error(f"Report not found for Case ID: `{cid}`. Please contact your Primary Health Centre.")
        st.stop()

    is_ai = p.get("review_mode") == "AI Provisional"
    ai_badge = """
    <div style="background-color: #fff3cd; border: 1px solid #ffeeba; color: #856404; padding: 10px; text-align: center; font-weight: bold; margin-bottom: 14px; font-size: 13px; border-radius: 4px;">
        ⚠️ PRELIMINARY AI-ASSISTED TRIAGE REPORT — FORMAL TELE-PATHOLOGY SIGN-OFF PENDING.
    </div>
    """ if is_ai else ""

    sign_html = f"""
    <div style="flex: 1; min-width: 140px; text-align: center; margin-top: 10px;">
        <span style="font-style: italic; color: #856404; font-size: 11px;">[AI Provisional]</span><br>
        <div style="border-bottom: 1px solid #111; margin: 8px 15px 4px 15px;"></div>
        <strong>AI Cytology Screener</strong>
    </div>
    """ if is_ai else f"""
    <div style="flex: 1; min-width: 140px; text-align: center; margin-top: 10px;">
        <div style="border-bottom: 1px solid #111; margin: 18px 15px 4px 15px;"></div>
        <strong>Pathologist Sign-off</strong><br>
        <span style="font-size: 11px;">{p.get('pathologist','')}</span>
    </div>
    """

    standalone_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * {{ box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; color: #111; margin: 0; padding: 10px; background: #fafafa; }}
        .slip-card {{ border: 2px solid #222; padding: 20px; background-color: #ffffff; max-width: 800px; margin: auto; line-height: 1.45; border-radius: 6px; box-shadow: 0 4px 10px rgba(0,0,0,0.06); }}
        .header {{ text-align: center; border-bottom: 2px solid #222; padding-bottom: 10px; margin-bottom: 14px; }}
        .header h2 {{ margin: 0; font-size: 18px; text-transform: uppercase; letter-spacing: 0.5px; }}
        .demo-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 6px 12px; font-size: 13px; margin-bottom: 14px; background: #fbfbfb; padding: 10px; border-radius: 4px; }}
        .section-box {{ border-top: 1px solid #888; padding: 10px 0; font-size: 13px; }}
        .advisory-box {{ border: 2px solid #111; padding: 12px; margin: 14px 0; background-color: #f8f9fa; font-size: 13px; }}
        .footer-signatures {{ display: flex; flex-wrap: wrap; justify-content: space-between; align-items: flex-end; gap: 16px; margin-top: 20px; font-size: 12px; }}
        .print-btn {{ display: block; width: 100%; max-width: 220px; margin: 0 auto 15px auto; padding: 10px; background-color: #0f172a; color: #ffffff; text-align: center; border-radius: 6px; cursor: pointer; font-weight: 600; font-size: 13px; text-decoration: none; border: none; }}
        @media print {{ .print-btn {{ display: none; }} body {{ padding: 0; background: #fff; }} .slip-card {{ border: 1px solid #000; box-shadow: none; width: 100%; }} }}
    </style>
    </head>
    <body>
    <button class="print-btn" onclick="window.print()">🖨️ Print / Save as PDF</button>
    <div class="slip-card">
        {ai_badge}
        <div class="header">
            <h2>PERIPHERAL BREAST TRIAGE UNIT</h2>
            <div style="font-size: 12px; font-weight: bold; color: #444; margin-top: 3px;">CLINICAL DECISION SUPPORT & TRIAGE ADVISORY REPORT</div>
        </div>
        <div class="demo-grid">
            <div><strong>Patient:</strong> {p['name']}</div>
            <div><strong>Age/Sex:</strong> {p['age']}y / Female</div>
            <div><strong>Case ID:</strong> {p['case_id']}</div>
            <div><strong>UHID:</strong> {p['uhid']}</div>
            <div><strong>Exam Date:</strong> {p['date_exam']}</div>
            <div><strong>Pincode:</strong> {p['pincode']}</div>
            <div style="grid-column: 1 / -1;"><strong>Examining MO:</strong> {p['referral_doc']}</div>
        </div>
        <div class="section-box">
            <strong>1. BEDSIDE CLINICAL & ULTRASOUND ASSESSMENT</strong><br>
            • <strong>Palpation:</strong> {p['cbe_mass']} | Size: {p['cbe_size']} | Axillary Nodes: {p['cbe_nodes']}<br>
            • <strong>Clinical Notes:</strong> {p.get('cbe_notes', 'N/A')}<br>
            • <strong>POCUS:</strong> {'Orientation: ' + p['pocus_orientation'] + ' | Margins: ' + p['pocus_margins'] if p['pocus_available'] else 'Not Performed / Unavailable'}
        </div>
        <div class="section-box">
            <strong>2. CYTOLOGY & TELE-PATHOLOGY CHAIN OF CUSTODY</strong><br>
            • <strong>Procedure:</strong> {p['fnac_passes']}<br>
            • <strong>Staining:</strong> {p['prep_tech']} ({p['staining']}) | Macro Adequacy: {p['macro_adequate']}<br>
            • <strong>IAC Yokohama:</strong> <strong>{p['yokohama']}</strong><br>
            • <strong>Observations:</strong> {p['path_notes']}<br>
            • <strong>Reviewer:</strong> {p.get('pathologist','')}
        </div>
        <div class="advisory-box">
            <div style="font-weight: bold; text-transform: uppercase;">3. TRIAGE & CONFIRMATORY ADVISORY</div>
            <p style="margin: 6px 0 3px 0;"><strong>Findings:</strong> Evaluated under triple assessment concordance protocol.</p>
        </div>
        <div class="footer-signatures">
            <div style="flex: 1.2; min-width: 180px;">
                <strong>Community Health Follow-up:</strong><br>
                ASHA Worker: {p.get('asha_worker', 'Unassigned')}<br>
                Contact: {p.get('asha_contact') if p.get('asha_contact') else 'Not Provided'}<br>
                Area: {p.get('asha_area', 'N/A')}
            </div>
            <div style="flex: 1; min-width: 140px; text-align: center; margin-top: 10px;">
                <div style="border-bottom: 1px solid #111; margin: 18px 15px 4px 15px;"></div>
                <strong>MO Sign-off</strong><br>
                <span style="font-size: 11px;">{p['referral_doc']}</span>
            </div>
            {sign_html}
        </div>
        <div style="border-top: 2px solid #222; margin-top: 18px; padding-top: 8px; text-align: center; font-size: 11px; font-weight: bold;">
            NOT DIAGNOSTIC. Triage Advisory for Clinical Decision Support. Proceed to Confirmatory Histopathology.
        </div>
    </div>
    </body>
    </html>
    """
    components.html(standalone_html, height=850, scrolling=True)
    st.stop()

# Helper: Whisper Voice-to-Text Dictation
def transcribe_voice_whisper(audio_bytes):
    if not audio_bytes:
        return ""
    if "GROQ_API_KEY" in st.secrets:
        try:
            api_key = st.secrets["GROQ_API_KEY"]
            headers = {"Authorization": f"Bearer {api_key}"}
            files = {"file": ("dictation.wav", audio_bytes, "audio/wav")}
            data = {"model": "whisper-large-v3-turbo", "temperature": 0.0}
            res = requests.post("https://api.groq.com/openai/v1/audio/transcriptions", headers=headers, files=files, data=data, timeout=15)
            if res.status_code == 200:
                return res.json().get("text", "").strip()
        except Exception as e:
            st.error(f"Whisper transcription error: {e}")
    return ""

def voice_text_input(label, current_val, key_prefix):
    c_in, c_mic = st.columns([5, 1])
    with c_mic:
        st.write("")
        st.write("")
        with st.popover("🎙️", help=f"Dictate {label}"):
            st.caption(f"Dictate: {label}")
            aud = st.audio_input("Record", key=f"aud_{key_prefix}")
            if aud:
                if st.button("Apply Voice", key=f"btn_{key_prefix}"):
                    spoken = transcribe_voice_whisper(aud.read())
                    if spoken:
                        st.session_state[f"val_{key_prefix}"] = spoken
                        st.rerun()
    with c_in:
        default_val = st.session_state.get(f"val_{key_prefix}", current_val)
        res = st.text_input(label, value=default_val, key=f"txt_{key_prefix}")
        st.session_state[f"val_{key_prefix}"] = res
        return res

def voice_text_area(label, current_val, key_prefix, height=120):
    c_in, c_mic = st.columns([5.5, 1])
    with c_mic:
        st.write("")
        st.write("")
        with st.popover("🎙️ Dictate", help=f"Dictate {label}"):
            st.caption(f"Speak findings for: {label}")
            aud = st.audio_input("Record audio", key=f"aud_{key_prefix}")
            if aud:
                if st.button("Append Transcript", key=f"btn_{key_prefix}"):
                    spoken = transcribe_voice_whisper(aud.read())
                    if spoken:
                        curr = st.session_state.get(f"val_{key_prefix}", current_val)
                        updated = f"{curr}\n• {spoken}".strip() if curr else spoken
                        st.session_state[f"val_{key_prefix}"] = updated
                        st.rerun()
    with c_in:
        default_val = st.session_state.get(f"val_{key_prefix}", current_val)
        res = st.text_area(label, value=default_val, key=f"txt_{key_prefix}", height=height)
        st.session_state[f"val_{key_prefix}"] = res
        return res
        # --- IMAGE QUALITY & SMEAR ADEQUACY HELPERS ---
def evaluate_image_quality(file_obj, threshold=70.0):
    try:
        file_bytes = np.asarray(bytearray(file_obj.read()), dtype=np.uint8)
        file_obj.seek(0)
        img = cv2.imdecode(file_bytes, cv2.IMREAD_GRAYSCALE)
        if img is None:
            return True, 100.0
        laplacian_var = cv2.Laplacian(img, cv2.CV_64F).var()
        return (laplacian_var >= threshold), round(laplacian_var, 1)
    except Exception:
        return True, 100.0

def analyze_smear_adequacy(file_obj, min_cluster_area=450):
    try:
        file_bytes = np.asarray(bytearray(file_obj.read()), dtype=np.uint8)
        file_obj.seek(0)
        bgr = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        if bgr is None:
            return 0, None, False, "Corrupted Image", False

        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
        lower_purple = np.array([115, 35, 30])
        upper_purple = np.array([165, 255, 215])
        nuclei_mask = cv2.inRange(hsv, lower_purple, upper_purple)

        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
        cluster_mask = cv2.morphologyEx(nuclei_mask, cv2.MORPH_CLOSE, kernel)
        clean_mask = cv2.morphologyEx(cluster_mask, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)))

        contours, _ = cv2.findContours(clean_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        annotated_bgr = bgr.copy()
        valid_clusters = 0
        has_mega_sheet = False
        total_pixels = bgr.shape[0] * bgr.shape[1]
        min_cluster_size = max(min_cluster_area, int(total_pixels * 0.0006))
        mega_sheet_threshold = int(total_pixels * 0.035)

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area >= min_cluster_size:
                valid_clusters += 1
                x, y, w, h = cv2.boundingRect(cnt)
                if area >= mega_sheet_threshold:
                    has_mega_sheet = True
                    box_color = (0, 255, 255)
                    label = f"Mega-Sheet #{valid_clusters} (Diagnostic)"
                else:
                    box_color = (0, 230, 77)
                    label = f"Cluster #{valid_clusters}"

                cv2.rectangle(annotated_bgr, (x, y), (x + w, y + h), box_color, 2)
                cv2.putText(annotated_bgr, label, (x, max(20, y - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, box_color, 1, cv2.LINE_AA)

        _, buffer = cv2.imencode(".jpg", annotated_bgr)
        annotated_bytes = buffer.tobytes()

        if has_mega_sheet or valid_clusters >= 4:
            status = "Adequate Cellularity (Diagnostic Architecture Present)"
            is_adequate = True
        elif 1 <= valid_clusters < 4:
            status = "Suboptimal in this Field (Check other fields)"
            is_adequate = False
        else:
            status = "Acellular Field"
            is_adequate = False

        return valid_clusters, annotated_bytes, is_adequate, status, has_mega_sheet
    except Exception as e:
        return 0, None, False, f"Analysis Error: {e}", False

def generate_whatsapp_link(phone, patient_name, case_id, risk_banner, action_directive):
    clean_digits = "".join(filter(str.isdigit, str(phone)))
    if len(clean_digits) == 10:
        clean_digits = "91" + clean_digits
    msg = (
        f"🚨 *BREAST TRIAGE ALERT: HIGH-PRIORITY REFERRAL*\n\n"
        f"• *Patient:* {patient_name}\n"
        f"• *Case ID:* {case_id}\n"
        f"• *Triage Status:* {risk_banner}\n"
        f"• *Required Action:* {action_directive}\n"
        f"• *Target Safety Window:* 21 Days\n\n"
        f"Please counsel patient at home and ensure core biopsy completion at District Hospital."
    )
    return f"https://wa.me/{clean_digits}?text={urllib.parse.quote(msg)}"

def generate_pathologist_alert_link(phone, patient):
    clean_digits = "".join(filter(str.isdigit, str(phone)))
    if len(clean_digits) == 10:
        clean_digits = "91" + clean_digits
    msg = (
        f"🔬 *NEW CYTOLOGY TELE-REVIEW REQUEST*\n\n"
        f"• *Patient:* {patient['name']} ({patient['age']}y)\n"
        f"• *Case ID:* `{patient['case_id']}` | *UHID:* `{patient['uhid']}`\n"
        f"• *Examining MO:* {patient['referral_doc']}\n"
        f"• *Palpation:* {patient['cbe_mass']}\n"
        f"• *Micrographs:* {len(patient.get('images', []))} attached\n"
        f"Please review slide images and submit tele-cytology sign-off."
    )
    return f"https://wa.me/{clean_digits}?text={urllib.parse.quote(msg)}"

def generate_mo_signoff_alert_link(phone, patient):
    clean_digits = "".join(filter(str.isdigit, str(phone)))
    if len(clean_digits) == 10:
        clean_digits = "91" + clean_digits
    msg = (
        f"✅ *CYTOLOGY REPORT SIGNED OFF & FINALIZED*\n\n"
        f"• *Patient:* {patient['name']} (Case ID: `{patient['case_id']}`)\n"
        f"• *Evaluating Pathologist:* {patient.get('pathologist', '')}\n"
        f"• *IAC Yokohama Category:* {patient.get('yokohama', '')}\n"
        f"• *Notes:* {patient.get('path_notes', 'N/A')}\n\n"
        f"Proceed to Module 4 to view CDSS Concordance Triage and print advisory report."
    )
    return f"https://wa.me/{clean_digits}?text={urllib.parse.quote(msg)}"

def generate_pdf_whatsapp_link(recipient_type, target_phone, patient, report_url):
    clean_digits = "".join(filter(str.isdigit, str(target_phone)))
    if len(clean_digits) == 10:
        clean_digits = "91" + clean_digits

    case_id = patient.get("case_id", "")
    p_name = patient.get("name", "")
    yokohama = patient.get("yokohama", "Under Evaluation")

    if recipient_type == "Patient / Family":
        msg = (
            f"नमस्ते {p_name} जी,\n\n"
            f"आपकी प्राथमिक स्तन जांच (Breast Triage Advisory) रिपोर्ट तैयार है।\n"
            f"• *केस आईडी:* `{case_id}`\n"
            f"• *जांच केंद्र:* {patient.get('referral_doc', 'Primary Health Centre')}\n\n"
            f"📄 *अपनी आधिकारिक रिपोर्ट देखने के लिए यहाँ क्लिक करें:* {report_url}\n\n"
            f"कृपया यह पर्ची अपनी आशा दीदी ({patient.get('asha_worker', '')}) या अस्पताल के डॉक्टर को दिखाएं।"
        )
    elif recipient_type == "Consulting Pathologist":
        msg = (
            f"🔬 *FINALIZED CYTOLOGY & TRIAGE ADVISORY ARCHIVE*\n\n"
            f"• *Patient:* {p_name} ({patient.get('age', '')}y, F)\n"
            f"• *Case ID:* `{case_id}` | *UHID:* `{patient.get('uhid', '')}`\n"
            f"• *Yokohama Category:* {yokohama}\n"
            f"• *Signed By:* {patient.get('pathologist', 'Pathologist')}\n\n"
            f"📥 *Digital Slip Link:* {report_url}"
        )
    elif recipient_type == "Examining Medical Officer (MO)":
        msg = (
            f"🩺 *BEDSIDE TRIAGE ADVISORY & CONCORDANCE SUMMARY*\n\n"
            f"• *Patient:* {p_name} | *Case ID:* `{case_id}`\n"
            f"• *Examining MO:* {patient.get('referral_doc', '')}\n"
            f"• *IAC Yokohama Result:* {yokohama}\n"
            f"• *Action Directive:* Core Biopsy referral status enclosed in advisory.\n\n"
            f"📄 *View/Print Signed PDF Slip:* {report_url}"
        )
    else:
        msg = (
            f"📋 *BREAST HEALTH TRIAGE RECORD*\n\n"
            f"• *Patient:* {p_name} (Case ID: `{case_id}`)\n"
            f"• *Status:* {yokohama}\n"
            f"• *Assigned ASHA:* {patient.get('asha_worker', 'N/A')}\n\n"
            f"📄 *Digital Report Link:* {report_url}"
        )

    return f"https://wa.me/{clean_digits}?text={urllib.parse.quote(msg)}"

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
            return {"url": image_url, "role": role, "uploader": uploader_name, "timestamp": timestamp_str}
        except Exception as e:
            st.error(f"Cloud image upload error: {e}")
    return {"file": file_obj, "role": role, "uploader": uploader_name, "timestamp": timestamp_str}

def delete_slide_image(image_item):
    if HAS_SUPABASE and "url" in image_item:
        try:
            filename = image_item["url"].split("/")[-1]
            supabase.storage.from_("slide-micrographs").remove([filename])
        except Exception as e:
            st.error(f"Cloud storage deletion error: {e}")

# Sidebar Selection
if "active_case_id" not in st.session_state or st.session_state.active_case_id not in st.session_state.patients:
    st.session_state.active_case_id = list(st.session_state.patients.keys())[0]

st.sidebar.title("🩺 Breast Triage CDSS")
st.sidebar.caption("Point-of-Care Triple Assessment + Whisper AI")

if HAS_SUPABASE:
    st.sidebar.success("🟢 Cloud Sync: Active (Supabase)")
else:
    st.sidebar.warning("🟡 Storage: RAM Session")

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
    st.caption("All text inputs support hands-free Whisper dictation (tap 🎙️ beside any field).")

    tab_edit, tab_register, tab_abha = st.tabs(["📝 View / Edit Current", "➕ Register New", "🪪 ABHA Auto-Fill"])

    with tab_abha:
        st.subheader("Fast Intake via ABHA QR Code Data")
        abha_raw = st.text_area(
            "Paste Scanned ABHA Card QR Text / JSON String:",
            placeholder='{"hid": "91-1234-5678-9012", "name": "Kavita Devi", "gender": "F", "dob": "1981-05-12", "pincode": "248001"}'
        )
        if st.button("Parse ABHA Data"):
            try:
                data = json.loads(abha_raw)
                calc_age = 45
                if "dob" in data:
                    birth_year = int(str(data["dob"])[:4])
                    calc_age = datetime.date.today().year - birth_year
                patient["name"] = data.get("name", patient["name"])
                patient["uhid"] = data.get("hid", data.get("healthId", patient["uhid"]))
                patient["age"] = int(data.get("age", calc_age))
                patient["pincode"] = str(data.get("pincode", patient["pincode"]))
                save_patient_record(patient)
                st.success("Demographics auto-filled from ABHA profile.")
                st.rerun()
            except Exception:
                st.error("Invalid QR format. Ensure standard ABHA JSON text is entered.")

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
            
            st.markdown("##### Community Health Worker Assignment")
            a1, a2, a3 = st.columns(3)
            new_asha_name = a1.text_input("ASHA Worker Name", "Meena Devi")
            new_asha_phone = a2.text_input("ASHA Phone (10 digits)", "")
            new_asha_area = a3.text_input("Assigned Sector / Village", "Sub-Center Sector 1")
            
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
                    "cbe_notes": "",
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
                    "asha_worker": new_asha_name,
                    "asha_contact": new_asha_phone,
                    "asha_area": new_asha_area,
                    "tracker_status": "Referral Pending (Counseling completed at PHC)",
                    "audit_log": [f"[{datetime.date.today()}] Record created by {new_doc}"]
                }
                save_patient_record(new_patient)
                st.session_state.active_case_id = new_case_id
                st.success(f"Case {new_case_id} registered successfully.")
                st.rerun()

    with tab_edit:
        st.subheader(f"Demographic & Clinical Profile: {patient['name']} ({patient['case_id']})")
        
        with st.expander("✏️ Edit Demographics & ASHA Assignment (Voice-Enabled)", expanded=False):
            ed1, ed2, ed3 = st.columns(3)
            patient["name"] = voice_text_input("Patient Full Name:", patient.get("name", ""), "mo_pname")
            patient["age"] = ed2.number_input("Age:", 15, 100, int(patient.get("age", 45)))
            patient["uhid"] = voice_text_input("UHID:", patient.get("uhid", ""), "mo_puhid")
            patient["pincode"] = voice_text_input("Pincode:", patient.get("pincode", ""), "mo_ppincode")
            patient["referral_doc"] = voice_text_input("Examining MO:", patient.get("referral_doc", ""), "mo_pdoc")

            st.markdown("##### Assigned ASHA / Community Health Worker")
            patient["asha_worker"] = voice_text_input("ASHA Worker Name:", patient.get("asha_worker", ""), "mo_ashaname")
            patient["asha_contact"] = voice_text_input("ASHA Phone Number:", patient.get("asha_contact", ""), "mo_ashaphone")
            patient["asha_area"] = voice_text_input("ASHA Assigned Area / Village:", patient.get("asha_area", ""), "mo_ashaarea")

            if st.button("Save Profile & ASHA Details"):
                patient["audit_log"].append(f"[{datetime.date.today()}] Profile updated by MO")
                save_patient_record(patient)
                st.success("Details updated.")

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
                index=2 if "Hard" in patient.get("cbe_mass", "") else (1 if "Firm" in patient.get("cbe_mass", "") else 0)
            )
            patient["cbe_size"] = voice_text_input("Approximate Mass Diameter (cm):", patient.get("cbe_size", "2.5 cm"), "mo_cbesize")
            patient["cbe_nodes"] = st.selectbox(
                "Ipsilateral Axillary Adenopathy:",
                ["Absent (Clinically negative)", "Present (Firm, Non-tender, or Matted)"],
                index=1 if "Present" in patient.get("cbe_nodes", "") else 0
            )
            patient["cbe_notes"] = voice_text_area("Clinical Palpation Notes & History (Dictate):", patient.get("cbe_notes", ""), "mo_cbenotes", height=90)
            patient["fnac_passes"] = voice_text_input("Needle Sampling Technique:", patient.get("fnac_passes", ""), "mo_fnacpasses")

        with col_right:
            st.markdown("#### Bedside Ultrasound (POCUS)")
            patient["pocus_available"] = st.checkbox("Ultrasound Available at Clinic?", value=patient.get("pocus_available", False))
            if patient["pocus_available"]:
                patient["pocus_orientation"] = st.radio(
                    "Lesion Orientation:",
                    ["Wider-than-tall (Horizontal / Parallel to skin)", "Taller-than-wide (Vertical growth / Transverse to skin)"],
                    index=1 if "Taller" in patient.get("pocus_orientation", "") else 0
                )
                patient["pocus_margins"] = st.radio(
                    "Margin Integrity:",
                    ["Smooth & Well-defined", "Irregular / Spiculated / Microlobulated"],
                    index=1 if "Irregular" in patient.get("pocus_margins", "") else 0
                )
                patient["pocus_posterior"] = st.radio(
                    "Posterior Acoustic Feature:",
                    ["Posterior acoustic enhancement (or neutral)", "Posterior acoustic shadowing (dark shadow behind mass)"],
                    index=1 if "shadowing" in patient.get("pocus_posterior", "") else 0
                )
            else:
                st.info("POCUS bypassed. Concordance engine will assess Clinical Suspicion + Cytology.")

        if st.button("Save Clinical & Ultrasound Findings"):
            save_patient_record(patient)
            st.success("Clinical exam data saved permanently.")

        st.divider()
        st.markdown("#### Direct Micrograph Upload with Blur Quality Gate")
        mo_new_files = st.file_uploader(
            "Add Slide Photos as MO:",
            type=["jpg", "png", "jpeg"],
            accept_multiple_files=True,
            key="mo_img_uploader"
        )
        if mo_new_files:
            if st.button("Upload MO Photos to Cloud"):
                blurry_files, valid_files = [], []
                for uploaded in mo_new_files:
                    is_sharp, sharpness = evaluate_image_quality(uploaded)
                    if not is_sharp:
                        blurry_files.append((uploaded.name, sharpness))
                    else:
                        valid_files.append(uploaded)

                if blurry_files:
                    for fname, score in blurry_files:
                        st.error(f"🚫 **Upload Blocked for `{fname}`** (Sharpness Score: `{score}` < `70.0`). Refocus microscope lens.")
                else:
                    for uploaded in valid_files:
                        img_entry = save_slide_image(uploaded, patient["case_id"], "Medical Officer", patient["referral_doc"])
                        patient["images"].append(img_entry)
                    patient["audit_log"].append(f"[{datetime.date.today()}] {len(valid_files)} photo(s) uploaded by MO")
                    save_patient_record(patient)
                    st.toast("✅ Micrographs uploaded successfully!", icon="🩺")
                    st.success(f"Attached {len(valid_files)} photo(s).")
                    st.rerun()

# Attached Micrographs Gallery (8 spaces)
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
                    
                    if st.button(f"🗑️ Delete #{idx+1}", key=f"mo_del_img_{patient['case_id']}_{idx}"):
                        delete_slide_image(item)
                        patient["images"].pop(idx)
                        patient["audit_log"].append(f"[{datetime.date.today()}] Slide #{idx+1} deleted by MO ({patient['referral_doc']})")
                        save_patient_record(patient)
                        st.success(f"Field #{idx+1} deleted.")
                        st.rerun()

        # Tele-Pathology Dispatch (8 spaces)
        st.divider()
        st.markdown("#### 📢 Tele-Pathology Dispatch")
        path_ph = voice_text_input("Pathologist WhatsApp Contact:", patient.get("pathologist_phone", "9876543210"), "mo_pathphone")
        patient["pathologist_phone"] = path_ph
        path_alert_url = generate_pathologist_alert_link(path_ph, patient)
        st.link_button("📲 Notify Pathologist via WhatsApp", path_alert_url)

# ==========================================
# MODULE 2: LAB TECHNICIAN (0 spaces)
# ==========================================
elif role == "2. Lab Technician (Staining, Patient Link & Upload)":
    st.header("2. Laboratory Technician: Slide Staining & Tele-Imaging")
    st.caption("Select a registered patient, record staining adequacy, append microscope photos, and use voice input.")

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
        patient["prep_tech"] = voice_text_input("Slide Prepared by (Technician Name):", patient.get("prep_tech", "Lab Tech"), "tech_prepname")
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
            index=0 if "Yes" in patient.get("macro_adequate", "") else 1
        )
        patient["tech_notes"] = voice_text_area("Lab Bench / Smear Notes (Dictate):", patient.get("tech_notes", ""), "tech_bench_notes", height=80)
        
        if st.button("Save Staining Details"):
            save_patient_record(patient)
            st.success("Staining details updated.")

    with col2:
        st.markdown("#### Smartphone Micrograph Upload & AI Adequacy Gate")
        tech_new_files = st.file_uploader(
            "Attach Slide Photos as Technician:",
            type=["jpg", "png", "jpeg"],
            accept_multiple_files=True,
            key="tech_img_uploader"
        )
        if tech_new_files:
            if st.button("🔬 Analyze Adequacy & Upload to Cloud"):
                blurry_files, processed_images = [], []
                total_detected_clusters = 0
                any_mega_sheet_found = False

                with st.spinner("Analyzing optical focus & cellular cluster density..."):
                    for uploaded in tech_new_files:
                        is_sharp, sharpness = evaluate_image_quality(uploaded)
                        if not is_sharp:
                            blurry_files.append((uploaded.name, sharpness))
                            continue

                        clusters, annotated_bytes, is_adeq, adeq_status, is_mega = analyze_smear_adequacy(uploaded)
                        total_detected_clusters += clusters
                        if is_mega:
                            any_mega_sheet_found = True

                        processed_images.append({
                            "file": uploaded,
                            "clusters": clusters,
                            "annotated": annotated_bytes,
                            "status": adeq_status,
                            "is_mega": is_mega
                        })

                if blurry_files:
                    for fname, score in blurry_files:
                        st.error(f"🚫 **Upload Rejected for `{fname}`** (Sharpness: `{score}` < 70.0). Refocus microscope.")
                elif processed_images:
                    st.markdown("##### Real-Time Cluster Detection Viewfinder:")
                    preview_cols = st.columns(min(len(processed_images), 3))
                    for idx, p_img in enumerate(processed_images):
                        with preview_cols[idx % 3]:
                            badge = " [Mega-Sheet Detected]" if p_img["is_mega"] else ""
                            st.image(p_img["annotated"], caption=f"{p_img['file'].name}: {p_img['clusters']} cluster(s){badge}", use_container_width=True)

                    smear_pass = any_mega_sheet_found or total_detected_clusters >= 4
                    if smear_pass:
                        st.success(f"✅ **SMEAR ADEQUATE:** Detected diagnostic epithelial cellularity ({total_detected_clusters} cluster(s) / sheets across fields).")
                    else:
                        st.warning(f"⚠️ **LOW CELLULARITY ({total_detected_clusters} clusters):** If other fields have cells, upload 2–3 more fields before patient leaves.")

                    for p_img in processed_images:
                        img_entry = save_slide_image(p_img["file"], patient["case_id"], "Lab Technician", patient["prep_tech"])
                        patient["images"].append(img_entry)

                    patient["macro_adequate"] = "Yes" if smear_pass else "Suboptimal (Low Cellularity on Tele-Screen)"
                    patient["audit_log"].append(f"[{datetime.date.today()}] {len(processed_images)} photo(s) analyzed: {total_detected_clusters} cluster(s).")
                    save_patient_record(patient)
                    st.toast("Micrographs uploaded and indexed.", icon="🔬")

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

                if st.button(f"🗑️ Delete #{idx+1}", key=f"tech_del_img_{patient['case_id']}_{idx}"):
                    delete_slide_image(item)
                    patient["images"].pop(idx)
                    patient["audit_log"].append(f"[{datetime.date.today()}] Slide #{idx+1} deleted by Tech ({patient['prep_tech']})")
                    save_patient_record(patient)
                    st.success(f"Field #{idx+1} deleted.")
                    st.rerun()

    st.divider()
    st.markdown("#### 📢 Dispatch Case to Consulting Pathologist")
    t_path_phone = voice_text_input("Pathologist WhatsApp Number:", patient.get("pathologist_phone", "9876543210"), "tech_path_phone")
    patient["pathologist_phone"] = t_path_phone
    tech_alert_url = generate_pathologist_alert_link(t_path_phone, patient)
    st.link_button("📲 Send Case to Pathologist (WhatsApp)", tech_alert_url)

# =========================================================
# MODULE 3: CYTOLOGY REVIEW (AI ASSISTANCE + REPORTING BOX)
# =========================================================
elif role == "3. Cytology Review (AI Assist & Pathologist Sign-Off)":
    st.header("3. Cytology Evaluation & Tele-Reporting Console")
    st.caption("AI-assisted pattern screening on the left; official pathologist reporting with Whisper voice dictation on the right.")

    st.subheader(f"Case Under Evaluation: {patient['name']} | Case ID: `{patient['case_id']}`")

    col_view, col_report = st.columns([1.1, 1.2], gap="medium")

    with col_view:
        st.markdown("### 🔬 Slide Viewer & Clinical Context")
        st.markdown(f"""
        * **Patient:** {patient['name']} ({patient['age']}y) | **UHID:** `{patient['uhid']}`
        * **Examining MO:** {patient['referral_doc']}
        * **Palpation (CBE):** {patient['cbe_mass']} (Nodes: {patient['cbe_nodes']})
        * **Clinical Notes:** {patient.get('cbe_notes', 'None recorded')}
        * **Rapid Stain:** {patient['prep_tech']} ({patient['staining']})
        """)

        st.divider()
        st.markdown(f"#### Attached Micrographs ({len(patient.get('images', []))} fields)")
        if patient.get("images"):
            for idx, item in enumerate(patient["images"]):
                caption_text = f"Field {idx+1} — By {item['role']} ({item['uploader']}) at {item.get('timestamp','')}"
                if "url" in item:
                    st.image(item["url"], caption=caption_text, use_container_width=True)
                elif "file" in item:
                    st.image(Image.open(item["file"]), caption=caption_text, use_container_width=True)
        else:
            st.warning("⚠️ No slide photos uploaded yet for this patient.")

        st.divider()
        st.markdown("### 🤖 AI Diagnostic Assistant (Reference Only)")
        ai_detected_pattern = st.selectbox(
            "AI Morphological Pattern Detection:",
            [
                "Cohesive antler-like sheets + naked bipolar nuclei (Favors Fibroadenoma)",
                "Loosely cohesive / discohesive atypical pleomorphic cells (High-Grade Malignancy)",
                "3D crowded clusters with mild atypia (Atypical / Equivocal)",
                "Hypocellular smear / proteinaceous fluid only (Inadequate / Dry Tap)"
            ],
            key="ai_pattern_selector"
        )

        if "Fibroadenoma" in ai_detected_pattern:
            suggested_cat = "Category 2: Benign Cells"
            suggested_risk = "<3%"
            draft_text = (
                "• Specimen & Stain: Breast FNAC; Romanowsky / Diff-Quik.\n"
                "• Cellularity & Architecture: High cellularity. Cohesive, monolayered, branching sheets of benign ductal epithelial cells in characteristic 'antler-like' configurations.\n"
                "• Nuclear Morphology: Small, round, monomorphic nuclei with regular spacing and delicate chromatin. No marked pleomorphism or hyperchromasia.\n"
                "• Background & Stroma: Abundant naked oval-to-elongated bipolar (myoepithelial) nuclei scattered across proteinaceous background with fragments of fibromyxoid stroma.\n"
                "• Impression: Consistent with Benign Fibroepithelial Lesion (Favors Fibroadenoma)."
            )
        elif "Malignancy" in ai_detected_pattern:
            suggested_cat = "Category 5: Malignant"
            suggested_risk = ">97%"
            draft_text = (
                "• Specimen & Stain: Breast FNAC; Romanowsky / Diff-Quik.\n"
                "• Cellularity & Architecture: Highly cellular smear dominated by dyscohesive, isolated intact atypical epithelial cells and irregular 3D clusters.\n"
                "• Nuclear Morphology: Marked pleomorphism, coarsely clumped chromatin, prominent nucleoli, and elevated N:C ratios.\n"
                "• Background & Stroma: Necrotic tumor background (tumor diathesis) with an absence of bare bipolar nuclei.\n"
                "• Impression: Cytologically malignant; features diagnostic of Carcinoma."
            )
        elif "Atypical" in ai_detected_pattern:
            suggested_cat = "Category 3: Atypical"
            suggested_risk = "15–50%"
            draft_text = (
                "• Specimen & Stain: Breast FNAC; Romanowsky / Diff-Quik.\n"
                "• Architecture: Crowded 3-dimensional groups with focal loss of cohesion.\n"
                "• Nuclear Features: Mild nuclear enlargement and chromatin clumping without overt malignant features.\n"
                "• Impression: Atypical features present; histopathologic correlation indicated."
            )
        else:
            suggested_cat = "Category 1: Insufficient / Inadequate"
            suggested_risk = "10–25%"
            draft_text = (
                "• Smear hypocellular, containing predominantly blood and proteinaceous debris.\n"
                "• Does not meet the IAC Yokohama threshold of 6 cohesive clusters of ductal epithelium."
            )

        st.markdown(f"> **AI Suggested:** `{suggested_cat}` ({suggested_risk} Risk)")
        with st.expander("📄 View AI Pre-Drafted Morphological Notes", expanded=False):
            st.code(draft_text, language="markdown")

    with col_report:
        st.markdown("### 📝 Official Pathologist Reporting Box")
        st.caption("Use live Whisper voice dictation (🎙️) or import the AI draft to quickly finalize findings.")

        if st.button("📥 Import AI Draft into Reporting Box"):
            patient["path_notes"] = draft_text
            patient["yokohama"] = suggested_cat
            st.session_state["val_path_obs"] = draft_text
            st.toast("AI draft copied to your reporting box!", icon="📋")
            st.rerun()

        patient["pathologist"] = voice_text_input(
            "Reporting Pathologist Name & Credentials:",
            patient.get("pathologist", "Dr. Priya Sharma, MD Pathology"),
            "path_name_input"
        )

        yokohama_categories = [
            "Category 1: Insufficient / Inadequate (Risk of Malignancy: 10–25%)",
            "Category 2: Benign Cells (Risk of Malignancy: <3%)",
            "Category 3: Atypical (Risk of Malignancy: 15–50%)",
            "Category 4: Suspicious for Malignancy (Risk of Malignancy: 60–85%)",
            "Category 5: Malignant (Risk of Malignancy: >97%)"
        ]
        curr_yok = patient.get("yokohama", yokohama_categories[1])
        matched_idx = next((i for i, cat in enumerate(yokohama_categories) if curr_yok[:10] in cat), 1)

        patient["yokohama"] = st.selectbox("Final IAC Yokohama Diagnostic Category:", options=yokohama_categories, index=matched_idx)

        patient["path_notes"] = voice_text_area(
            "Microscopic Observations & Remarks (Dictate with Whisper):",
            patient.get("path_notes", ""),
            "path_obs",
            height=200
        )

        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("💾 Submit & Sign Official Report", type="primary"):
                patient["review_mode"] = "Final Pathologist Sign-Off"
                patient["audit_log"].append(f"[{datetime.date.today()}] Cytology signed off by {patient['pathologist']} ({patient['yokohama'][:10]})")
                save_patient_record(patient)
                st.success("Official report signed and committed.")
                st.session_state["show_mo_notify"] = True

        with col_btn2:
            if st.button("⚡ Save as Provisional (AI Assist Only)"):
                patient["review_mode"] = "AI Provisional"
                patient["pathologist"] = "AI Computer-Aided Screener (Provisional)"
                patient["audit_log"].append(f"[{datetime.date.today()}] Provisional AI classification saved ({patient['yokohama'][:10]})")
                save_patient_record(patient)
                st.warning("Saved as provisional advisory.")

        if st.session_state.get("show_mo_notify") or patient.get("review_mode") == "Final Pathologist Sign-Off":
            st.divider()
            st.markdown("#### 📢 Dispatch Report to Examining MO")
            mo_phone = voice_text_input("Frontline MO / PHC Clinic WhatsApp Number:", patient.get("mo_contact", "9876543210"), "path_mo_phone")
            patient["mo_contact"] = mo_phone
            mo_notify_url = generate_mo_signoff_alert_link(mo_phone, patient)
            st.link_button("📲 Notify MO of Sign-Off via WhatsApp", mo_notify_url)
            # ==========================================
# MODULE 4: CDSS TRIAGE & FORMAL REPORT
# ==========================================
elif role == "4. CDSS Triage & Advisory Report":
    st.header(f"4. CDSS Triage Advisory: {patient['name']} ({patient['case_id']})")

    is_ai_mode = patient.get("review_mode") == "AI Provisional"
    if is_ai_mode:
        st.warning("⚠️ **NOTICE: THIS REPORT USES PROVISIONAL AI CYTOLOGY INFERENCE. AWAITING PATHOLOGIST REVIEW.**")

    cbe_suspicious = "Hard, Irregular" in patient.get("cbe_mass", "") or "Present" in patient.get("cbe_nodes", "")
    usg_suspicious = False
    if patient.get("pocus_available"):
        usg_suspicious = (
            "Taller-than-wide" in patient.get("pocus_orientation", "") or
            "Irregular" in patient.get("pocus_margins", "") or
            "shadowing" in patient.get("pocus_posterior", "")
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
            "Invasive carcinomas with dense fibrous stroma frequently produce hypocellular aspirates. "
            "An inadequate smear in this setting must be managed with high suspicion."
        )
        action_text = "BYPASS REPEAT FNAB. PROCEED DIRECTLY TO CORE-NEEDLE BIOPSY (CNB)."

    elif not clinical_high_risk and "Category 1: Insufficient" in yokohama:
        status_banner = "INSUFFICIENT SAMPLING (LOW CLINICAL SUSPICION)"
        status_color = "orange"
        analysis_text = "Cytology sample contains inadequate diagnostic epithelial groups (Baseline Risk: 10%–25%)."
        action_text = "REPEAT GUIDED FNAB OR REFER FOR DIAGNOSTIC BREAST ULTRASOUND within 2–3 weeks."

    elif "Category 4: Suspicious" in yokohama or "Category 5: Malignant" in yokohama:
        status_banner = "CONCORDANT SUSPICIOUS / MALIGNANT PROFILE"
        status_color = "red"
        analysis_text = "Cytomorphological features unequivocally identify or strongly favor neoplasia (Risk: 60% to >97%)."
        action_text = "URGENT TERTIARY REFERRAL for Core Biopsy (for ER, PR, HER2 profiling) and definitive oncology staging."

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

    # --- MULTI-CADRE WHATSAPP DISPATCH CONSOLE ---
    st.divider()
    st.markdown("### 📤 Dispatch Official Report via WhatsApp")
    st.caption("Patients receive a private link showing ONLY their signed report slip (no app interface or tools).")

    r_col1, r_col2 = st.columns([1.5, 2])
    recipient_type = r_col1.selectbox(
        "Send Report To:",
        [
            "Patient / Family",
            "Examining Medical Officer (MO)",
            "Consulting Pathologist",
            "Assigned ASHA Worker",
            "Specific / Custom Contact"
        ]
    )

    if recipient_type == "Patient / Family":
        default_phone = patient.get("patient_contact", "")
    elif recipient_type == "Examining Medical Officer (MO)":
        default_phone = patient.get("mo_contact", "9876543210")
    elif recipient_type == "Consulting Pathologist":
        default_phone = patient.get("pathologist_phone", "9876543210")
    elif recipient_type == "Assigned ASHA Worker":
        default_phone = patient.get("asha_contact", "")
    else:
        default_phone = ""

    target_phone = r_col2.text_input(
        f"Recipient WhatsApp Number ({recipient_type}):",
        value=default_phone,
        placeholder="Enter 10-digit mobile number"
    )

    app_base_url = "https://breast-triage-cdss.streamlit.app"
    standalone_report_link = f"{app_base_url}/?view=report&case_id={patient['case_id']}"

    if target_phone:
        custom_wa_url = generate_pdf_whatsapp_link(recipient_type, target_phone, patient, standalone_report_link)
        c_act1, c_act2 = st.columns([2, 1])
        c_act1.link_button(f"📲 Send Official Slip to {recipient_type} (WhatsApp)", custom_wa_url, use_container_width=True)
        if c_act2.button("Log Dispatch Event"):
            patient["audit_log"].append(
                f"[{datetime.date.today()}] Report link dispatched via WhatsApp to {recipient_type} ({target_phone})"
            )
            save_patient_record(patient)
            st.success("Dispatch logged in audit trail.")
    else:
        st.info("💡 Enter a phone number above to activate the WhatsApp dispatch link.")

    st.divider()
    st.subheader("Formal Monochromatic Clinical Advisory Slip")

    p = patient
    ai_watermark = """
    <div style="background-color: #fff3cd; border: 1px solid #ffeeba; color: #856404; padding: 10px; text-align: center; font-weight: bold; margin-bottom: 14px; font-size: 13px; border-radius: 4px;">
        ⚠️ PRELIMINARY AI-ASSISTED TRIAGE REPORT — FORMAL TELE-PATHOLOGY SIGN-OFF PENDING.
    </div>
    """ if is_ai_mode else ""

    sign_off_html = f"""
    <div style="flex: 1; min-width: 140px; text-align: center; margin-top: 10px;">
        <span style="font-style: italic; color: #856404; font-size: 11px;">[AI Provisional]</span><br>
        <div style="border-bottom: 1px solid #111; margin: 8px 15px 4px 15px;"></div>
        <strong>AI Cytology Screener</strong>
    </div>
    """ if is_ai_mode else f"""
    <div style="flex: 1; min-width: 140px; text-align: center; margin-top: 10px;">
        <div style="border-bottom: 1px solid #111; margin: 18px 15px 4px 15px;"></div>
        <strong>Pathologist Sign-off</strong><br>
        <span style="font-size: 11px;">{p.get('pathologist','')}</span>
    </div>
    """

    report_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * {{ box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; color: #111; margin: 0; padding: 10px; background: transparent; }}
        .slip-card {{
            border: 2px solid #222;
            padding: 20px;
            background-color: #ffffff;
            max-width: 800px;
            margin: auto;
            line-height: 1.45;
        }}
        .header {{ text-align: center; border-bottom: 2px solid #222; padding-bottom: 10px; margin-bottom: 14px; }}
        .header h2 {{ margin: 0; font-size: 18px; text-transform: uppercase; letter-spacing: 0.5px; }}
        .header .sub {{ font-size: 12px; font-weight: bold; color: #444; margin-top: 3px; }}
        .demo-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
            gap: 6px 12px;
            font-size: 13px;
            margin-bottom: 14px;
            background: #fbfbfb;
            padding: 10px;
            border-radius: 4px;
        }}
        .section-box {{
            border-top: 1px solid #888;
            padding: 10px 0;
            font-size: 13px;
        }}
        .advisory-box {{
            border: 2px solid #111;
            padding: 12px;
            margin: 14px 0;
            background-color: #f8f9fa;
            font-size: 13px;
        }}
        .footer-signatures {{
            display: flex;
            flex-wrap: wrap;
            justify-content: space-between;
            align-items: flex-end;
            gap: 16px;
            margin-top: 20px;
            font-size: 12px;
        }}
        .print-btn {{
            display: block;
            width: 100%;
            max-width: 220px;
            margin: 0 auto 15px auto;
            padding: 10px;
            background-color: #0f172a;
            color: #ffffff;
            text-align: center;
            border-radius: 6px;
            cursor: pointer;
            font-weight: 600;
            font-size: 13px;
            text-decoration: none;
            border: none;
        }}
        @media print {{
            .print-btn {{ display: none; }}
            body {{ padding: 0; }}
            .slip-card {{ border: 1px solid #000; padding: 15px; width: 100%; }}
        }}
    </style>
    </head>
    <body>

    <button class="print-btn" onclick="window.print()">🖨️ Print / Save as PDF</button>

    <div class="slip-card">
        {ai_watermark}
        <div class="header">
            <h2>PERIPHERAL BREAST TRIAGE UNIT</h2>
            <div class="sub">CLINICAL DECISION SUPPORT & TRIAGE ADVISORY REPORT</div>
        </div>

        <div class="demo-grid">
            <div><strong>Patient:</strong> {p['name']}</div>
            <div><strong>Age/Sex:</strong> {p['age']}y / Female</div>
            <div><strong>Case ID:</strong> {p['case_id']}</div>
            <div><strong>UHID:</strong> {p['uhid']}</div>
            <div><strong>Exam Date:</strong> {p['date_exam']}</div>
            <div><strong>Pincode:</strong> {p['pincode']}</div>
            <div style="grid-column: 1 / -1;"><strong>Examining MO:</strong> {p['referral_doc']}</div>
        </div>

        <div class="section-box">
            <strong>1. BEDSIDE CLINICAL & ULTRASOUND ASSESSMENT</strong><br>
            • <strong>Palpation (CBE):</strong> {p['cbe_mass']} | Size: {p['cbe_size']} | Axillary Nodes: {p['cbe_nodes']}<br>
            • <strong>Clinical Notes:</strong> {p.get('cbe_notes', 'N/A')}<br>
            • <strong>POCUS:</strong> {'Orientation: ' + p['pocus_orientation'] + ' | Margins: ' + p['pocus_margins'] + ' | ' + p['pocus_posterior'] if p['pocus_available'] else 'Not Performed / Unavailable'}
        </div>

        <div class="section-box">
            <strong>2. CYTOLOGY & TELE-PATHOLOGY CHAIN OF CUSTODY</strong><br>
            • <strong>Procedure:</strong> {p['fnac_passes']}<br>
            • <strong>Slide Stained By:</strong> {p['prep_tech']} ({p['staining']}) | Macro Adequacy: {p['macro_adequate']}<br>
            • <strong>Micrographs:</strong> {len(p.get('images', []))} attached image(s)<br>
            • <strong>IAC Yokohama:</strong> <span style="text-decoration: underline; font-weight: bold;">{p['yokohama']}</span><br>
            • <strong>Assessment Mode:</strong> {p.get('review_mode','Final')}<br>
            • <strong>Observations:</strong> {p['path_notes']}<br>
            • <strong>Reviewer:</strong> {p.get('pathologist','')}
        </div>

        <div class="advisory-box">
            <div style="font-weight: bold; text-transform: uppercase;">3. TRIAGE & CONFIRMATORY ADVISORY: {prefix}{status_banner}</div>
            <p style="margin: 6px 0 3px 0;"><strong>Analysis:</strong> {analysis_text}</p>
            <p style="margin: 3px 0;"><strong>Directive:</strong> <strong>{action_text}</strong></p>
        </div>

        <div class="footer-signatures">
            <div style="flex: 1.2; min-width: 180px;">
                <strong>Community Tracker:</strong><br>
                ASHA: {p.get('asha_worker', 'Unassigned')}<br>
                Contact: {p.get('asha_contact') if p.get('asha_contact') else 'Not Provided'}<br>
                Area: {p.get('asha_area') if p.get('asha_area') else p.get('pincode', 'N/A')}<br>
                Safety Window: 21 Days
            </div>
            <div style="flex: 1; min-width: 140px; text-align: center; margin-top: 10px;">
                <div style="border-bottom: 1px solid #111; margin: 18px 15px 4px 15px;"></div>
                <strong>MO Sign-off</strong><br>
                <span style="font-size: 11px;">{p['referral_doc']}</span>
            </div>
            {sign_off_html}
        </div>

        <div style="border-top: 2px solid #222; margin-top: 18px; padding-top: 8px; text-align: center; font-size: 11px; font-weight: bold;">
            **NOT DIAGNOSTIC. Triage Advisory for Clinical Decision Support. Proceed to Confirmatory Histopathology.**
        </div>
    </div>
    </body>
    </html>
    """
    components.html(report_html, height=820, scrolling=True)

# ==========================================
# MODULE 5: ASHA CLOSED-LOOP TRACKER
# ==========================================
elif role == "5. ASHA Closed-Loop Tracker":
    st.header(f"5. ASHA Community Follow-Up Tracking: {patient['name']}")
    st.caption("Monitor tertiary referral completion within the 21-day window to eliminate loss-to-follow-up.")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### ASHA Worker Assignment & Contact (Voice-Enabled)")
        patient["asha_worker"] = voice_text_input("ASHA Worker Name:", patient.get("asha_worker", ""), "asha_name_trk")
        patient["asha_contact"] = voice_text_input("ASHA Contact Number:", patient.get("asha_contact", ""), "asha_cont_trk")
        patient["asha_area"] = voice_text_input("Assigned Area / Sector / Village:", patient.get("asha_area", ""), "asha_area_trk")
        patient["asha_notes"] = voice_text_area("Home Visit Counseling Notes (Dictate):", patient.get("asha_notes", ""), "asha_home_notes", height=90)
        
        if st.button("Update ASHA Worker Details"):
            patient["audit_log"].append(f"[{datetime.date.today()}] ASHA details updated by worker ({patient['asha_worker']})")
            save_patient_record(patient)
            st.success("ASHA contact and notes updated.")

        if patient.get("asha_contact"):
            alert_url = generate_whatsapp_link(
                patient["asha_contact"],
                patient["name"],
                patient["case_id"],
                patient.get("yokohama", "Under Evaluation"),
                "Complete district hospital referral visit within 21-day safety window."
            )
            st.link_button("📲 Send Follow-Up Reminder via WhatsApp", alert_url)

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
            f"{patient.get('asha_worker', '')} ({patient.get('asha_area', '')})"
        ]
    }
    st.table(summary_data)

    st.markdown("#### Chronological Activity Log")
    for log_item in patient.get("audit_log", []):
        st.code(log_item, language="markdown")
            
