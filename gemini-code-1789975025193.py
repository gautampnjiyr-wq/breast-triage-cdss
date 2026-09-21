import datetime
import uuid
import urllib.parse
import json
import re
import requests
import base64
import streamlit as st
import streamlit.components.v1 as components
from PIL import Image
import numpy as np
import cv2
import pandas as pd

st.set_page_config(
    page_title="Breast Triage CDSS",
    page_icon="🩺",
    layout="wide"
)

# =========================================================================
# MODERN MEDICAL UI THEME & GLOBAL CSS
# =========================================================================
st.markdown("""
    <style>
        .stApp {
            background-color: #f8fafc;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        }
        div.stContainer {
            background-color: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.03), 0 2px 4px -1px rgba(0, 0, 0, 0.02);
            margin-bottom: 16px;
        }
        .badge-success { background-color: #dcfce7; color: #166534; padding: 4px 12px; border-radius: 9999px; font-weight: 600; font-size: 11px; display: inline-block; }
        .badge-warning { background-color: #fef3c7; color: #92400e; padding: 4px 12px; border-radius: 9999px; font-weight: 600; font-size: 11px; display: inline-block; }
        .badge-danger { background-color: #fee2e2; color: #991b1b; padding: 4px 12px; border-radius: 9999px; font-weight: 600; font-size: 11px; display: inline-block; }
        .badge-info { background-color: #e0f2fe; color: #0369a1; padding: 4px 12px; border-radius: 9999px; font-weight: 600; font-size: 11px; display: inline-block; }
        .st-emotion-cache-16txtl3 { visibility: hidden; }
    </style>
""", unsafe_allow_html=True)

# =========================================================================
# DATABASE / SUPABASE INITIALIZATION
# =========================================================================
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
                "patient_contact": "9876543210",
                "mo_contact": "9876543210",
                "pathologist_phone": "9876543210",
                "cbe_mass": "Hard, Irregular (Tethered/Fixed to skin or fascia)",
                "cbe_size": "4.0 cm",
                "cbe_nodes": "Present (Firm, Non-tender, or Matted)",
                "cbe_notes": "Firm irregular retroareolar mass with mild skin tethering.",
                "birads_score": "BI-RADS 5: Highly Suggestive of Malignancy",
                "pocus_available": True,
                "pocus_orientation": "Taller-than-wide (Vertical growth / Transverse to skin)",
                "pocus_margins": "Irregular / Spiculated / Microlobulated",
                "pocus_posterior": "Posterior acoustic shadowing (dark shadow behind mass)",
                "fnac_passes": "2 passes (23G Needle, Capillary method)",
                "prep_tech": "Lab Tech Sarah Khan",
                "staining": "Diff-Quik (90-second rapid Romanowsky)",
                "macro_adequate": "Yes (Chalky/white granular fragments visible against light)",
                "tech_notes": "Rapid air-dried Romanowsky smear.",
                "images": [],
                "review_mode": "Final Pathologist Sign-Off",
                "pathologist": "Dr. Priya Sharma, MD Pathology",
                "yokohama": "Category 5: Malignant",
                "yokohama_rom": ">97% Risk of Malignancy",
                "robinson_dissociation": "Mostly isolated cells (3)",
                "robinson_size": ">4× lymphocyte (3)",
                "robinson_uniformity": "Marked pleomorphism (3)",
                "robinson_nucleoli": "Prominent (3)",
                "robinson_margin": "Markedly irregular (3)",
                "robinson_chromatin": "Coarse / clumped (3)",
                "robinson_score": 18,
                "robinson_grade": "Grade III (High Grade)",
                "nottingham_tubules": "Little or none (<10%) (3)",
                "nottingham_pleomorphism": "Marked pleomorphism (3)",
                "nottingham_mitoses": ">12 mitoses/10 HPF (3)",
                "nottingham_score": 9,
                "nottingham_grade": "Grade III (Poorly Differentiated)",
                "path_notes": "Marked dyscohesion, pleomorphism, and prominent nucleoli.",
                "asha_worker": "Meena Devi",
                "asha_contact": "9876543210",
                "asha_area": "Sub-Center Raipur, Sector 4",
                "asha_notes": "Home visit completed. Advised patient on adherence.",
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
            try:
                safe_payload = patient_dict.copy()
                extended_cols = [
                    "patient_contact", "mo_contact", "pathologist_phone", 
                    "cbe_notes", "tech_notes", "asha_notes", "asha_contact", "asha_area",
                    "birads_score", "yokohama_rom", "robinson_dissociation", "robinson_size", 
                    "robinson_uniformity", "robinson_nucleoli", "robinson_margin", 
                    "robinson_chromatin", "robinson_score", "robinson_grade",
                    "nottingham_tubules", "nottingham_pleomorphism", "nottingham_mitoses",
                    "nottingham_score", "nottingham_grade"
                ]
                for col in extended_cols:
                    safe_payload.pop(col, None)
                if isinstance(safe_payload.get("date_exam"), (datetime.date, datetime.datetime)):
                    safe_payload["date_exam"] = safe_payload["date_exam"].isoformat()
                supabase.table("patients").upsert(safe_payload).execute()
            except Exception as inner_e:
                st.error(f"Cloud sync warning: {inner_e}")
    st.session_state.patients[patient_dict["case_id"]] = patient_dict

st.session_state.patients = fetch_patient_registry()

# =========================================================================
# HELPER FUNCTIONS (VOICE, CV2 ADEQUACY, WHATSAPP, STORAGE, BASE64)
# =========================================================================
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

def get_image_render_src(image_item):
    try:
        if "url" in image_item:
            return image_item["url"]
        elif "file" in image_item:
            file_obj = image_item["file"]
            file_obj.seek(0.0)
            encoded = base64.b64encode(file_obj.read()).decode("utf-8")
            file_obj.seek(0.0)
            return f"data:image/jpeg;base64,{encoded}"
    except Exception:
        pass
    return ""

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
        f"• *IAC Yokohama:* {patient.get('yokohama', '')}\n"
        f"• *Robinson Grade:* {patient.get('robinson_grade', 'N/A')}\n"
        f"• *Nottingham Grade:* {patient.get('nottingham_grade', 'N/A')}\n\n"
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
            f"आपकी प्राथमिक स्तन जांच (Breast Triage Advisory) रिपोर्ट तैयार है。\n"
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
            f"• *Robinson Grade:* {patient.get('robinson_grade', 'N/A')}\n"
            f"• *Nottingham Grade:* {patient.get('nottingham_grade', 'N/A')}\n\n"
            f"📥 *Digital Slip Link:* {report_url}"
        )
    elif recipient_type == "Examining Medical Officer (MO)":
        msg = (
            f"🩺 *BEDSIDE TRIAGE ADVISORY & CONCORDANCE SUMMARY*\n\n"
            f"• *Patient:* {p_name} | *Case ID:* `{case_id}`\n"
            f"• *Examining MO:* {patient.get('referral_doc', '')}\n"
            f"• *IAC Yokohama Result:* {yokohama}\n"
            f"• *Robinson Grade:* {patient.get('robinson_grade', 'N/A')}\n"
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
    <div style="background-color: #fff3cd; border: 1px solid #ffeeba; color: #856404; padding: 10px; text-align: center; font-weight: bold; margin-bottom: 14px; font-size: 13px; border-radius: 8px;">
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

    lab_images = [item for item in p.get("images", []) if item.get('role') != "Clinical Image"]
    img_html = ""
    if lab_images:
        img_html = "<div style='margin-top: 12px; border-top: 1px dashed #cbd5e1; padding-top: 10px;'><strong>Attached Slide Micrographs & Laboratory Records:</strong><div style='display: flex; gap: 10px; flex-wrap: wrap; margin-top: 8px;'>"
        for item in lab_images:
            src_str = get_image_render_src(item)
            if src_str:
                img_html += f"<div style='border: 1px solid #cbd5e1; padding: 4px; border-radius: 6px; text-align: center; background: #f8fafc;'><img src='{src_str}' style='max-height: 120px; display: block; border-radius: 4px;'><span style='font-size: 10px; font-weight: bold; color: #334155;'>{item.get('role','Slide')}</span></div>"
        img_html += "</div></div>"

    standalone_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * {{ box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; color: #0f172a; margin: 0; padding: 10px; background: #f8fafc; }}
        .slip-card {{ border: 1px solid #cbd5e1; padding: 24px; background-color: #ffffff; max-width: 800px; margin: auto; line-height: 1.5; border-radius: 12px; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.05); }}
        .header {{ text-align: center; border-bottom: 2px solid #0f172a; padding-bottom: 12px; margin-bottom: 16px; }}
        .header h2 {{ margin: 0; font-size: 20px; text-transform: uppercase; letter-spacing: 0.5px; color: #0f172a; }}
        .demo-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 8px 14px; font-size: 13px; margin-bottom: 16px; background: #f8fafc; padding: 12px; border-radius: 8px; border: 1px solid #e2e8f0; }}
        .section-box {{ border-top: 1px solid #cbd5e1; padding: 12px 0; font-size: 13px; color: #334155; }}
        .advisory-box {{ border: 1px solid #0f172a; padding: 14px; margin: 16px 0; background-color: #f1f5f9; border-radius: 8px; font-size: 13px; color: #0f172a; }}
        .footer-signatures {{ display: flex; flex-wrap: wrap; justify-content: space-between; align-items: flex-end; gap: 16px; margin-top: 24px; font-size: 12px; }}
        .print-btn {{ display: block; width: 100%; max-width: 220px; margin: 0 auto 20px auto; padding: 10px; background-color: #0f172a; color: #ffffff; text-align: center; border-radius: 8px; cursor: pointer; font-weight: 600; font-size: 13px; text-decoration: none; border: none; }}
        @media print {{ .print-btn {{ display: none; }} body {{ padding: 0; background: #fff; }} .slip-card {{ border: 1px solid #000; box-shadow: none; width: 100%; }} }}
    </style>
    </head>
    <body>
    <button class="print-btn" onclick="window.print()">🖨️ Print / Save as PDF</button>
    <div class="slip-card">
        {ai_badge}
        <div class="header">
            <h2>PERIPHERAL BREAST TRIAGE UNIT</h2>
            <div style="font-size: 12px; font-weight: 600; color: #475569; margin-top: 4px;">CLINICAL DECISION SUPPORT & TRIAGE ADVISORY REPORT</div>
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
            • <strong>Clinical Notes:</strong> {p.get('cbe_notes', 'None recorded')}<br>
            • <strong>BI-RADS Score:</strong> {p.get('birads_score', 'N/A')}<br>
            • <strong>POCUS:</strong> {'Orientation: ' + p['pocus_orientation'] + ' | Margins: ' + p['pocus_margins'] if p['pocus_available'] else 'Not Performed / Unavailable'}
        </div>
        <div class="section-box">
            <strong>2. CYTOLOGY & TELE-PATHOLOGY CHAIN OF CUSTODY</strong><br>
            • <strong>Procedure:</strong> {p['fnac_passes']}<br>
            • <strong>Slide Stained By:</strong> {p['prep_tech']} ({p['staining']}) | Macro Adequacy: {p['macro_adequate']}<br>
            • <strong>IAC Yokohama Category:</strong> <strong>{p['yokohama']}</strong><br>
            • <strong>Estimated Risk of Malignancy (ROM):</strong> <span style="color: #991b1b; font-weight: bold;">{p.get('yokohama_rom', 'N/A')}</span><br>
            • <strong>Robinson Cytological Grade:</strong> <span style="font-weight:bold;">{p.get('robinson_grade', 'N/A')} (Score: {p.get('robinson_score', 'N/A')}/18)</span><br>
            • <strong>Nottingham Histological Grade:</strong> <span style="font-weight:bold;">{p.get('nottingham_grade', 'N/A')} (Score: {p.get('nottingham_score', 'N/A')}/9)</span><br>
            • <strong>Pathologist Observations:</strong> {p['path_notes']}<br>
            • <strong>Reviewer:</strong> {p.get('pathologist','')}<br>
            {img_html}
        </div>
        <div class="advisory-box">
            <div style="font-weight: bold; text-transform: uppercase;">3. TRIAGE & CONFIRMATORY ADVISORY</div>
            <p style="margin: 6px 0 3px 0;"><strong>Findings:</strong> Evaluated under triple assessment concordance protocol.</p>
        </div>
        <div class="footer-signatures">
            <div style="flex: 1.2; min-width: 180px;">
                <strong>Community Tracker:</strong><br>
                ASHA: {p.get('asha_worker', 'Unassigned')}<br>
                Contact: {p.get('asha_contact') if p.get('asha_contact') else 'Not Provided'}<br>
                Area: {p.get('asha_area', 'N/A')}<br>
                Safety Window: 21 Days
            </div>
            <div style="flex: 1; min-width: 140px; text-align: center; margin-top: 10px;">
                <div style="border-bottom: 1px solid #111; margin: 18px 15px 4px 15px;"></div>
                <strong>MO Sign-off</strong><br>
                <span style="font-size: 11px;">{p['referral_doc']}</span>
            </div>
            {sign_html}
        </div>
        <div style="border-top: 1px solid #cbd5e1; margin-top: 20px; padding-top: 10px; text-align: center; font-size: 11px; font-weight: bold; color: #475569;">
            **NOT DIAGNOSTIC. Triage Advisory for Clinical Decision Support. Proceed to Confirmatory Histopathology.**
        </div>
    </div>
    </body>
    </html>
    """
    components.html(standalone_html, height=850, scrolling=True)
    st.stop()

# =========================================================================
# MODERN SIDEBAR STATE & NAVIGATION
# =========================================================================
if "active_case_id" not in st.session_state or st.session_state.active_case_id not in st.session_state.patients:
    st.session_state.active_case_id = list(st.session_state.patients.keys())[0]

st.sidebar.markdown("### 🩺 Breast Triage CDSS")
st.sidebar.caption("Point-of-Care Triple Assessment + Whisper AI")

if HAS_SUPABASE:
    st.sidebar.markdown('<span class="badge-success">🟢 Cloud Sync Active</span>', unsafe_allow_html=True)
else:
    st.sidebar.markdown('<span class="badge-warning">🟡 RAM Session Storage</span>', unsafe_allow_html=True)

st.sidebar.write("")
case_options = list(st.session_state.patients.keys())
selected_case = st.sidebar.selectbox(
    "Active Patient Case:",
    options=case_options,
    index=case_options.index(st.session_state.active_case_id) if st.session_state.active_case_id in case_options else 0
)
st.session_state.active_case_id = selected_case
patient = st.session_state.patients[st.session_state.active_case_id]

st.sidebar.markdown("---")
if patient.get("review_mode") == "Final Pathologist Sign-Off":
    st.sidebar.markdown('<span class="badge-success">● Pathologist Reviewed</span>', unsafe_allow_html=True)
elif patient.get("review_mode") == "AI Provisional":
    st.sidebar.markdown('<span class="badge-warning">⚡ AI Provisional Triage</span>', unsafe_allow_html=True)
else:
    st.sidebar.markdown('<span class="badge-info">⏳ Awaiting Review</span>', unsafe_allow_html=True)

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
        "6. Audit Trail & Provenance (Who Did What)",
        "7. Advanced Batch Excel Validator & Analytics"
    ]
)

# =========================================================================
# MODULE 1: MEDICAL OFFICER
# =========================================================================
if role == "1. Medical Officer (Exam, POCUS & Direct Upload)":
    st.header("1. Medical Officer: Clinical Examination & Bedside Staging")
    st.caption("All text inputs support hands-free Whisper dictation (tap 🎙️ beside any field).")

    with st.expander("📖 Official BI-RADS & Ultrasound (POCUS) Correlation Reference Matrix", expanded=False):
        st.markdown("""
        | BI-RADS Category | Expected USG Shape / Orientation | USG Margin Integrity | Posterior Acoustic Feature | Malignancy Risk | CDSS Triage Action |
        | :--- | :--- | :--- | :--- | :--- | :--- |
        | **BI-RADS 2** | Wider-than-tall (Parallel) | Smooth & Well-defined | Enhancement / Neutral | **0% (Benign)** | Routine Follow-up |
        | **BI-RADS 3** | Wider-than-tall (Parallel) | Smooth or Faint Lobulated | Neutral / Mild Enhancement | **< 2% (Probably Benign)** | Short-term 6-mo Follow-up |
        | **BI-RADS 4 (a/b/c)** | Variable / Vertical tendency | Irregular / Microlobulated | Shadowing or Mixed | **2% – 95% (Suspicious)** | **Mandate Core-Needle Biopsy** |
        | **BI-RADS 5** | Taller-than-wide (Vertical) | Spiculated / Highly Irregular | Prominent Shadowing | **> 95% (Malignant)** | **Mandate CNB & Urgent Referral** |
        """)

    tab_edit, tab_register, tab_abha = st.tabs(["📝 View / Edit Current", "➕ Register New", "🪪 ABHA Auto-Fill"])

    with tab_abha:
        with st.container(border=True):
            st.subheader("Fast Intake via ABHA QR Code Data")
            abha_raw = st.text_area(
                "Paste Scanned ABHA Card QR Text / JSON String:",
                placeholder='{"hidn":"21-4560-1406-6251","hid":"21456014066251@abdm","name":"GEETHA","gender":"F","dob":"24-01-2003","mobile":"9843187603","address":"105, WEST STREET..."}',
                key="input_abha_qr_raw"
            )
            if st.button("Parse ABHA Data", key="btn_parse_abha_unique"):
                try:
                    data = json.loads(abha_raw.strip())
                    dob_str = str(data.get("dob", "")).strip()
                    calc_age = patient.get("age", 45)

                    if dob_str:
                        try:
                            if re.search(r"^\d{1,2}[-/]\d{1,2}[-/]\d{4}$", dob_str):
                                birth_year = int(dob_str[-4:])
                                calc_age = datetime.date.today().year - birth_year
                            elif re.search(r"^\d{4}[-/]\d{1,2}[-/]\d{1,2}$", dob_str):
                                birth_year = int(dob_str[:4])
                                calc_age = datetime.date.today().year - birth_year
                            elif re.search(r"^\d{4}$", dob_str):
                                birth_year = int(dob_str)
                                calc_age = datetime.date.today().year - birth_year
                        except Exception:
                            pass

                    raw_age = data.get("age")
                    if raw_age is not None:
                        try:
                            calc_age = int(raw_age)
                        except Exception:
                            pass

                    extracted_uhid = data.get("hidn") or data.get("hid") or data.get("healthId") or patient.get("uhid", "")
                    
                    extracted_pin = data.get("pincode")
                    if not extracted_pin and "address" in data:
                        pin_match = re.search(r"\b\d{6}\b", str(data["address"]))
                        if pin_match:
                            extracted_pin = pin_match.group(0)

                    patient["name"] = data.get("name", patient["name"])
                    patient["uhid"] = str(extracted_uhid)
                    patient["age"] = int(calc_age)
                    if extracted_pin:
                        patient["pincode"] = str(extracted_pin)
                    
                    mobile_val = data.get("mobile") or data.get("phone")
                    if mobile_val:
                        patient["patient_contact"] = str(mobile_val)

                    patient["audit_log"].append(f"[{datetime.date.today()}] Profile auto-populated from official ABHA QR code ({patient['uhid']})")
                    save_patient_record(patient)
                    st.success(f"✅ ABHA Verified: {patient['name']} ({patient['age']} yrs) | ABHA ID: {patient['uhid']}")
                    st.rerun()

                except Exception as e:
                    st.error(f"Failed to parse ABHA data: {e}. Please ensure valid JSON was pasted.")

    with tab_register:
        with st.container(border=True):
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
                        "patient_contact": "",
                        "mo_contact": "9876543210",
                        "pathologist_phone": "9876543210",
                        "cbe_mass": "Firm, Discrete, Moderately mobile",
                        "cbe_size": "2.5 cm",
                        "cbe_nodes": "Absent (Clinically negative)",
                        "cbe_notes": "",
                        "birads_score": "BI-RADS 2: Benign",
                        "pocus_available": False,
                        "pocus_orientation": "Wider-than-tall (Horizontal / Parallel to skin)",
                        "pocus_margins": "Smooth & Well-defined",
                        "pocus_posterior": "Posterior acoustic enhancement (or neutral)",
                        "fnac_passes": "2 passes (23G Needle, Capillary method)",
                        "prep_tech": "Unassigned",
                        "staining": "Diff-Quik (90-second rapid Romanowsky)",
                        "macro_adequate": "Pending Assessment",
                        "tech_notes": "",
                        "images": [],
                        "review_mode": "Awaiting Review",
                        "pathologist": "Pending Review",
                        "yokohama": "Category 1: Insufficient / Inadequate",
                        "yokohama_rom": "10–25% Risk of Malignancy",
                        "robinson_dissociation": "Mostly cohesive clusters (1)",
                        "robinson_size": "1–2× lymphocyte (1)",
                        "robinson_uniformity": "Uniform / monomorphic (1)",
                        "robinson_nucleoli": "Inconspicuous (1)",
                        "robinson_margin": "Smooth (1)",
                        "robinson_chromatin": "Fine (1)",
                        "robinson_score": 6,
                        "robinson_grade": "Grade I (Low Grade)",
                        "nottingham_tubules": "Complete tubular formation (>75%) (1)",
                        "nottingham_pleomorphism": "Small, uniform cells (1)",
                        "nottingham_mitoses": "Up to 7 mitoses/10 HPF (1)",
                        "nottingham_score": 3,
                        "nottingham_grade": "Grade I (Well Differentiated)",
                        "path_notes": "Awaiting slide image review.",
                        "asha_worker": new_asha_name,
                        "asha_contact": new_asha_phone,
                        "asha_area": new_asha_area,
                        "asha_notes": "",
                        "tracker_status": "Referral Pending (Counseling completed at PHC)",
                        "audit_log": [f"[{datetime.date.today()}] Record created by {new_doc}"]
                    }
                    save_patient_record(new_patient)
                    st.session_state.active_case_id = new_case_id
                    st.success(f"Case {new_case_id} registered successfully.")
                    st.rerun()

    with tab_edit:
        with st.container(border=True):
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

                if st.button("Save Profile & ASHA Details", key="btn_save_profile_mo"):
                    patient["audit_log"].append(f"[{datetime.date.today()}] Profile updated by MO")
                    save_patient_record(patient)
                    st.success("Details updated.")

        with st.container(border=True):
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
                st.markdown("#### Bedside Ultrasound & BI-RADS Staging")
                
                birads_options = [
                    "BI-RADS 1: Negative",
                    "BI-RADS 2: Benign",
                    "BI-RADS 3: Probably Benign",
                    "BI-RADS 4a: Low Suspicion for Malignancy",
                    "BI-RADS 4b: Moderate Suspicion for Malignancy",
                    "BI-RADS 4c: High Suspicion for Malignancy",
                    "BI-RADS 5: Highly Suggestive of Malignancy"
                ]
                
                curr_birads = str(patient.get("birads_score") or "BI-RADS 2: Benign")
                birads_idx = 1
                for i, b in enumerate(birads_options):
                    if curr_birads.strip().lower() in b.lower() or b.lower().startswith(curr_birads.strip().lower()[:5]):
                        birads_idx = i
                        break
                        
                patient["birads_score"] = st.selectbox("ACR BI-RADS Assessment Score:", options=birads_options, index=birads_idx)

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

            if st.button("Save Clinical & Ultrasound Findings", key="btn_save_findings_mo"):
                save_patient_record(patient)
                st.success("Clinical exam data saved permanently.")

        with st.container(border=True):
            st.markdown("#### Direct Clinical Notes Upload")
            mo_new_files = st.file_uploader(
                "Add Clinical Photos / Gross Examination / Scans as MO:",
                type=["jpg", "png", "jpeg"],
                accept_multiple_files=True,
                key="mo_img_uploader"
            )
            if mo_new_files:
                if st.button("Upload Clinical Photos to Cloud", key="btn_upload_mo_photos"):
                    blurry_files, valid_files = [], []
                    for uploaded in mo_new_files:
                        is_sharp, sharpness = evaluate_image_quality(uploaded)
                        if not is_sharp:
                            blurry_files.append((uploaded.name, sharpness))
                        else:
                            valid_files.append(uploaded)

                    if blurry_files:
                        for fname, score in blurry_files:
                            st.error(f"🚫 **Upload Blocked for `{fname}`** (Sharpness Score: `{score}` < `70.0`).")
                    else:
                        for uploaded in valid_files:
                            img_entry = save_slide_image(uploaded, patient["case_id"], "Clinical Image", patient["referral_doc"])
                            patient["images"].append(img_entry)
                        patient["audit_log"].append(f"[{datetime.date.today()}] {len(valid_files)} clinical photo(s) uploaded by MO")
                        save_patient_record(patient)
                        st.toast("✅ Clinical images uploaded successfully!", icon="🩺")
                        st.success(f"Attached {len(valid_files)} clinical photo(s).")
                        st.rerun()

            if patient.get("images"):
                st.divider()
                st.markdown(f"#### Attached Visual Records ({len(patient['images'])} total)")
                img_cols = st.columns(min(len(patient["images"]), 4))
                for idx, item in enumerate(patient["images"]):
                    with img_cols[idx % 4]:
                        role_tag = item.get('role', 'Clinical Image')
                        caption_str = f"#{idx+1} [{role_tag}]"
                        if "url" in item:
                            st.image(item["url"], caption=caption_str, use_container_width=True)
                        elif "file" in item:
                            st.image(Image.open(item["file"]), caption=caption_str, use_container_width=True)
                        
                        if st.button(f"🗑️ Delete #{idx+1}", key=f"mo_del_img_{patient['case_id']}_{idx}"):
                            delete_slide_image(item)
                            patient["images"].pop(idx)
                            patient["audit_log"].append(f"[{datetime.date.today()}] Visual record #{idx+1} deleted by MO")
                            save_patient_record(patient)
                            st.success(f"Record #{idx+1} deleted.")
                            st.rerun()

        with st.container(border=True):
            st.markdown("#### 📢 Tele-Pathology Dispatch")
            path_ph = voice_text_input("Pathologist WhatsApp Contact:", patient.get("pathologist_phone", "9876543210"), "mo_pathphone")
            patient["pathologist_phone"] = path_ph
            path_alert_url = generate_pathologist_alert_link(path_ph, patient)
            st.link_button("📲 Notify Pathologist via WhatsApp", path_alert_url)

# =========================================================================
# MODULE 2: LAB TECHNICIAN
# =========================================================================
elif role == "2. Lab Technician (Staining, Patient Link & Upload)":
    st.header("2. Laboratory Technician: Slide Staining & Tele-Imaging")
    st.caption("Select a registered patient, record staining adequacy, append microscope photos, and use voice input.")

    with st.container(border=True):
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

    with st.container(border=True):
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
            
            if st.button("Save Staining Details", key="btn_save_stain_tech"):
                save_patient_record(patient)
                st.success("Staining details updated.")

        with col2:
            st.markdown("#### Micrograph Upload & AI Adequacy Gate")
            tech_img_role = st.selectbox("Image Classification Role:", ["Cytology Micrograph", "Histopathology Slide"], key="tech_img_role_sel")
            tech_new_files = st.file_uploader(
                "Attach Slide Photos as Technician:",
                type=["jpg", "png", "jpeg"],
                accept_multiple_files=True,
                key="tech_img_uploader"
            )
            if tech_new_files:
                if st.button("🔬 Analyze Adequacy & Upload to Cloud", key="btn_analyze_upload_tech"):
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
                            img_entry = save_slide_image(p_img["file"], patient["case_id"], tech_img_role, patient["prep_tech"])
                            patient["images"].append(img_entry)

                        patient["macro_adequate"] = "Yes" if smear_pass else "Suboptimal (Low Cellularity on Tele-Screen)"
                        patient["audit_log"].append(f"[{datetime.date.today()}] {len(processed_images)} {tech_img_role}(s) uploaded.")
                        save_patient_record(patient)
                        st.toast("Micrographs uploaded and indexed.", icon="🔬")

    if patient.get("images"):
        with st.container(border=True):
            st.markdown(f"#### Attached Visual Records ({len(patient['images'])} total)")
            img_cols = st.columns(min(len(patient["images"]), 4))
            for idx, item in enumerate(patient["images"]):
                with img_cols[idx % 4]:
                    role_str = item.get('role', 'Micrograph')
                    if "url" in item:
                        st.image(item["url"], caption=f"Field {idx+1} [{role_str}]", use_container_width=True)
                    elif "file" in item:
                        st.image(Image.open(item["file"]), caption=f"Field {idx+1} [{role_str}]", use_container_width=True)

                    if st.button(f"🗑️ Delete #{idx+1}", key=f"tech_del_img_{patient['case_id']}_{idx}"):
                        delete_slide_image(item)
                        patient["images"].pop(idx)
                        patient["audit_log"].append(f"[{datetime.date.today()}] Record #{idx+1} deleted by Tech")
                        save_patient_record(patient)
                        st.success(f"Record #{idx+1} deleted.")
                        st.rerun()

    with st.container(border=True):
        st.markdown("#### 📢 Dispatch Case to Consulting Pathologist")
        t_path_phone = voice_text_input("Pathologist WhatsApp Number:", patient.get("pathologist_phone", "9876543210"), "tech_path_phone")
        patient["pathologist_phone"] = t_path_phone
        tech_alert_url = generate_pathologist_alert_link(t_path_phone, patient)
        st.link_button("📲 Send Case to Pathologist (WhatsApp)", tech_alert_url)

# =========================================================================
# MODULE 3: CYTOLOGY REVIEW & NOTTINGHAM HISTOPATHOLOGY GRADING
# =========================================================================
elif role == "3. Cytology Review (AI Assist & Pathologist Sign-Off)":
    st.header("3. Cytology Evaluation & Tele-Reporting Console")
    st.caption("AI screening on the left; official pathologist reporting with Robinson & Nottingham grading on the right.")

    st.subheader(f"Case Under Evaluation: {patient['name']} | Case ID: `{patient['case_id']}`")

    col_view, col_report = st.columns([1.1, 1.2], gap="medium")

    with col_view:
        with st.container(border=True):
            st.markdown("### 🔬 Slide Viewer & Clinical Context")
            st.markdown(f"""
            * **Patient:** {patient['name']} ({patient['age']}y) | **UHID:** `{patient['uhid']}`
            * **Examining MO:** {patient['referral_doc']}
            * **BI-RADS Score:** {patient.get('birads_score', 'N/A')}
            * **Palpation (CBE):** {patient['cbe_mass']} (Nodes: {patient['cbe_nodes']})
            * **Clinical Notes:** {patient.get('cbe_notes', 'None recorded')}
            * **Rapid Stain:** {patient['prep_tech']} ({patient['staining']})
            """)

            st.divider()
            st.markdown(f"#### Attached Visual Records ({len(patient.get('images', []))} fields)")
            if patient.get("images"):
                for idx, item in enumerate(patient["images"]):
                    role_tag = item.get('role', 'Micrograph')
                    caption_text = f"Field {idx+1} — [{role_tag}] By {item['uploader']} at {item.get('timestamp','')}"
                    if "url" in item:
                        st.image(item["url"], caption=caption_text, use_container_width=True)
                    elif "file" in item:
                        st.image(Image.open(item["file"]), caption=caption_text, use_container_width=True)
            else:
                st.warning("⚠️ No images uploaded yet for this patient.")

        with st.container(border=True):
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
                suggested_rom = "<3% Risk of Malignancy"
                draft_text = "• Specimen & Stain: Breast FNAC; Romanowsky / Diff-Quik.\n• Cellularity & Architecture: High cellularity. Cohesive, monolayered, branching sheets of benign ductal epithelial cells in characteristic 'antler-like' configurations.\n• Impression: Consistent with Benign Fibroepithelial Lesion (Favors Fibroadenoma)."
            elif "Malignancy" in ai_detected_pattern:
                suggested_cat = "Category 5: Malignant"
                suggested_rom = ">97% Risk of Malignancy"
                draft_text = "• Specimen & Stain: Breast FNAC; Romanowsky / Diff-Quik.\n• Cellularity & Architecture: Highly cellular smear dominated by dyscohesive, isolated intact atypical epithelial cells and irregular 3D clusters.\n• Impression: Cytologically malignant; features diagnostic of Carcinoma."
            elif "Atypical" in ai_detected_pattern:
                suggested_cat = "Category 3: Atypical"
                suggested_rom = "15–50% Risk of Malignancy"
                draft_text = "• Specimen & Stain: Breast FNAC; Romanowsky / Diff-Quik.\n• Architecture: Crowded 3-dimensional groups with focal loss of cohesion.\n• Impression: Atypical features present; histopathologic correlation indicated."
            else:
                suggested_cat = "Category 1: Insufficient / Inadequate"
                suggested_rom = "10–25% Risk of Malignancy"
                draft_text = "• Smear hypocellular, containing predominantly blood and proteinaceous debris."

            st.markdown(f"> **AI Suggested:** `{suggested_cat}` ({suggested_rom})")
            with st.expander("📄 View AI Pre-Drafted Morphological Notes", expanded=False):
                st.code(draft_text, language="markdown")

    with col_report:
        with st.container(border=True):
            st.markdown("### 📝 Official Pathologist Reporting Box")
            st.caption("Use live Whisper voice dictation (🎙️) or import the AI draft to quickly finalize findings.")

            if st.button("📥 Import AI Draft into Reporting Box", key="btn_import_ai_draft"):
                patient["path_notes"] = draft_text
                patient["yokohama"] = suggested_cat
                patient["yokohama_rom"] = suggested_rom
                st.session_state["val_path_obs"] = draft_text
                st.toast("AI draft copied to your reporting box!", icon="📋")
                st.rerun()

            patient["pathologist"] = voice_text_input(
                "Reporting Pathologist Name & Credentials:",
                patient.get("pathologist", "Dr. Priya Sharma, MD Pathology"),
                "path_name_input"
            )

            yokohama_options = [
                ("Category 1: Insufficient / Inadequate", "10–25% Risk of Malignancy"),
                ("Category 2: Benign Cells", "<3% Risk of Malignancy"),
                ("Category 3: Atypical", "15–50% Risk of Malignancy"),
                ("Category 4: Suspicious for Malignancy", "60–85% Risk of Malignancy"),
                ("Category 5: Malignant", ">97% Risk of Malignancy")
            ]
            
            curr_yok = str(patient.get("yokohama") or yokohama_options[1][0])
            yok_idx = 1
            for i, opt in enumerate(yokohama_options):
                if opt[0][:10].lower() in curr_yok.lower():
                    yok_idx = i
                    break

            selected_yok = st.selectbox("Final IAC Yokohama Diagnostic Category:", options=[opt[0] for opt in yokohama_options], index=yok_idx)
            patient["yokohama"] = selected_yok
            patient["yokohama_rom"] = next(opt[1] for opt in yokohama_options if opt[0] == selected_yok)

            st.markdown(f"<span style='color: #991b1b; font-weight: bold;'>Estimated Malignancy Risk (ROM): {patient['yokohama_rom']}</span>", unsafe_allow_html=True)

            st.markdown("---")
            st.markdown("#### 📊 Robinson Cytological Grading (Pre-op FNAC)")
            r1_opts = [("Mostly cohesive clusters (1)", 1), ("Moderate dissociation (2)", 2), ("Mostly isolated cells (3)", 3)]
            r2_opts = [("1–2× lymphocyte (1)", 1), ("2–4× lymphocyte (2)", 2), (">4× lymphocyte (3)", 3)]
            r3_opts = [("Uniform / monomorphic (1)", 1), ("Moderate pleomorphism (2)", 2), ("Marked pleomorphism (3)", 3)]
            r4_opts = [("Inconspicuous (1)", 1), ("Noticeable (2)", 2), ("Prominent (3)", 3)]
            r5_opts = [("Smooth (1)", 1), ("Slightly irregular (2)", 2), ("Markedly irregular (3)", 3)]
            r6_opts = [("Fine (1)", 1), ("Granular (2)", 2), ("Coarse / clumped (3)", 3)]

            def get_idx(opts, val):
                for i, opt in enumerate(opts):
                    if val and opt[0][:5] in val:
                        return i
                return 0

            cr1, cr2 = st.columns(2)
            with cr1:
                r1 = st.selectbox("1. Cell dissociation", r1_opts, index=get_idx(r1_opts, patient.get("robinson_dissociation")), format_func=lambda x: x[0], key="rob_diss")
                r2 = st.selectbox("2. Cell size", r2_opts, index=get_idx(r2_opts, patient.get("robinson_size")), format_func=lambda x: x[0], key="rob_size")
                r3 = st.selectbox("3. Cell uniformity", r3_opts, index=get_idx(r3_opts, patient.get("robinson_uniformity")), format_func=lambda x: x[0], key="rob_unif")
            with cr2:
                r4 = st.selectbox("4. Nucleoli", r4_opts, index=get_idx(r4_opts, patient.get("robinson_nucleoli")), format_func=lambda x: x[0], key="rob_nucl")
                r5 = st.selectbox("5. Nuclear margin", r5_opts, index=get_idx(r5_opts, patient.get("robinson_margin")), format_func=lambda x: x[0], key="rob_marg")
                r6 = st.selectbox("6. Chromatin", r6_opts, index=get_idx(r6_opts, patient.get("robinson_chromatin")), format_func=lambda x: x[0], key="rob_chrom")

            rob_total = r1[1] + r2[1] + r3[1] + r4[1] + r5[1] + r6[1]
            rob_grade = "Grade I (Low Grade)" if rob_total <= 11 else ("Grade II (Intermediate)" if rob_total <= 14 else "Grade III (High Grade)")
            st.markdown(f"**Robinson Score:** `{rob_total}/18` | **Grade:** {rob_grade}")

            patient["robinson_dissociation"] = r1[0]
            patient["robinson_size"] = r2[0]
            patient["robinson_uniformity"] = r3[0]
            patient["robinson_nucleoli"] = r4[0]
            patient["robinson_margin"] = r5[0]
            patient["robinson_chromatin"] = r6[0]
            patient["robinson_score"] = rob_total
            patient["robinson_grade"] = rob_grade

            st.markdown("---")
            st.markdown("#### 🔬 Nottingham Histological Grading (Confirmatory Biopsy)")
            n1_opts = [("Complete tubular formation (>75%) (1)", 1), ("Moderate tubular formation (10-75%) (2)", 2), ("Little or none (<10%) (3)", 3)]
            n2_opts = [("Small, uniform cells (1)", 1), ("Moderate nuclear size and variation (2)", 2), ("Marked pleomorphism (3)", 3)]
            n3_opts = [("Up to 7 mitoses/10 HPF (1)", 1), ("8–12 mitoses/10 HPF (2)", 2), (">12 mitoses/10 HPF (3)", 3)]

            nc1, nc2, nc3 = st.columns(3)
            with nc1:
                n_tub = st.selectbox("1. Tubules", n1_opts, index=get_idx(n1_opts, patient.get("nottingham_tubules")), format_func=lambda x: x[0], key="n_tub")
            with nc2:
                n_pleo = st.selectbox("2. Pleomorphism", n2_opts, index=get_idx(n2_opts, patient.get("nottingham_pleomorphism")), format_func=lambda x: x[0], key="n_pleo")
            with nc3:
                n_mit = st.selectbox("3. Mitotic Count", n3_opts, index=get_idx(n3_opts, patient.get("nottingham_mitoses")), format_func=lambda x: x[0], key="n_mit")

            nott_total = n_tub[1] + n_pleo[1] + n_mit[1]
            nott_grade = "Grade I (Well Differentiated)" if nott_total <= 5 else ("Grade II (Moderately Differentiated)" if nott_total <= 7 else "Grade III (Poorly Differentiated)")
            st.markdown(f"**Nottingham Score:** `{nott_total}/9` | **Grade:** {nott_grade}")

            patient["nottingham_tubules"] = n_tub[0]
            patient["nottingham_pleomorphism"] = n_pleo[0]
            patient["nottingham_mitoses"] = n_mit[0]
            patient["nottingham_score"] = nott_total
            patient["nottingham_grade"] = nott_grade

            st.markdown("---")
            patient["path_notes"] = voice_text_area("Pathology Remarks (Whisper):", patient.get("path_notes", ""), "path_obs", height=140)

            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                if st.button("💾 Submit & Sign Official Report", type="primary", key="btn_submit_sign_path"):
                    patient["review_mode"] = "Final Pathologist Sign-Off"
                    patient["audit_log"].append(f"[{datetime.date.today()}] Cytology signed off by {patient['pathologist']}")
                    save_patient_record(patient)
                    st.success("Report signed and committed.")
                    st.session_state["show_mo_notify"] = True
            with col_btn2:
                if st.button("⚡ Save as Provisional", key="btn_save_provisional_ai"):
                    patient["review_mode"] = "AI Provisional"
                    patient["pathologist"] = "AI Screener (Provisional)"
                    save_patient_record(patient)
                    st.warning("Saved as provisional.")

            if st.session_state.get("show_mo_notify") or patient.get("review_mode") == "Final Pathologist Sign-Off":
                st.divider()
                mo_phone = voice_text_input("MO WhatsApp Number:", patient.get("mo_contact", "9876543210"), "path_mo_phone")
                patient["mo_contact"] = mo_phone
                st.link_button("📲 Notify MO via WhatsApp", generate_mo_signoff_alert_link(mo_phone, patient))

# =========================================================================
# MODULE 4: CDSS TRIAGE & FORMAL REPORT
# =========================================================================
elif role == "4. CDSS Triage & Advisory Report":
    with st.container(border=True):
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

        if clinical_high_risk and "Category 2: Benign" in yokohama:
            status_banner = "CRITICAL DISCORDANCE (HIGH RISK FLAGS)"
            status_color = "red"
            analysis_text = "Physical examination and/or bedside ultrasound demonstrate high-suspicion features, yet cytology is reported as benign. Residual risk remains ~20%–30%."
            action_text = "CONFIRMATORY CORE-NEEDLE BIOPSY IS MANDATORY."

        elif clinical_high_risk and "Category 1: Insufficient" in yokohama:
            status_banner = "HIGH-RISK INADEQUACY (SUSPECTED DESMOPLASTIC MASS)"
            status_color = "red"
            analysis_text = "High clinical suspicion with inadequate cytology cellularity."
            action_text = "BYPASS REPEAT FNAB. PROCEED DIRECTLY TO CORE-NEEDLE BIOPSY (CNB)."

        elif "Category 4" in yokohama or "Category 5" in yokohama:
            status_banner = "CONCORDANT SUSPICIOUS / MALIGNANT PROFILE"
            status_color = "red"
            analysis_text = f"Cytomorphological features indicate neoplasia. ROM: {patient.get('yokohama_rom','')}"
            action_text = "URGENT TERTIARY REFERRAL for Core Biopsy and definitive oncology staging."

        elif "Category 3: Atypical" in yokohama:
            status_banner = "ATYPICAL CYTOLOGY (EQUIVOCAL)"
            status_color = "orange"
            analysis_text = "Smear exhibits architectural or nuclear atypia (ROM: 15%–50%)."
            action_text = "REFER FOR HISTOPATHOLOGIC EVALUATION (Core-Needle Biopsy)."

        else:
            status_banner = "CONCORDANT BENIGN PROFILE"
            status_color = "green"
            analysis_text = "Clinical, sonographic, and cytomorphological findings align without suspicious features."
            action_text = "ROUTINE CLINICAL REVIEW in 3–6 months."

        prefix = "[PROVISIONAL AI ASSIST] " if is_ai_mode else ""
        if status_color == "red":
            st.error(f"🚨 **{prefix}{status_banner}**\n\n**Analysis:** {analysis_text}\n\n**Directive:** {action_text}")
        elif status_color == "orange":
            st.warning(f"⚠️ **{prefix}{status_banner}**\n\n**Analysis:** {analysis_text}\n\n**Directive:** {action_text}")
        else:
            st.success(f"✅ **{prefix}{status_banner}**\n\n**Analysis:** {analysis_text}\n\n**Directive:** {action_text}")

    with st.container(border=True):
        st.subheader("Formal Monochromatic Clinical Advisory Slip")

        p = patient
        ai_watermark = """
        <div style="background-color: #fff3cd; border: 1px solid #ffeeba; color: #856404; padding: 10px; text-align: center; font-weight: bold; margin-bottom: 14px; font-size: 13px; border-radius: 8px;">
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

        lab_images = [item for item in p.get("images", []) if item.get('role') != "Clinical Image"]
        img_html = ""
        if lab_images:
            img_html = "<div style='margin-top: 12px; border-top: 1px dashed #cbd5e1; padding-top: 10px;'><strong>Attached Slide Micrographs & Laboratory Records:</strong><div style='display: flex; gap: 10px; flex-wrap: wrap; margin-top: 8px;'>"
            for item in lab_images:
                src_str = get_image_render_src(item)
                if src_str:
                    img_html += f"<div style='border: 1px solid #cbd5e1; padding: 4px; border-radius: 6px; text-align: center; background: #f8fafc;'><img src='{src_str}' style='max-height: 120px; display: block; border-radius: 4px;'><span style='font-size: 10px; font-weight: bold; color: #334155;'>{item.get('role','Slide')}</span></div>"
            img_html += "</div></div>"

        report_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            * {{ box-sizing: border-box; }}
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; color: #0f172a; margin: 0; padding: 10px; background: transparent; }}
            .slip-card {{ border: 1px solid #cbd5e1; padding: 24px; background-color: #ffffff; max-width: 800px; margin: auto; line-height: 1.5; border-radius: 12px; }}
            .header {{ text-align: center; border-bottom: 2px solid #0f172a; padding-bottom: 12px; margin-bottom: 16px; }}
            .header h2 {{ margin: 0; font-size: 20px; text-transform: uppercase; letter-spacing: 0.5px; color: #0f172a; }}
            .header .sub {{ font-size: 12px; font-weight: 600; color: #475569; margin-top: 4px; }}
            .demo-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 8px 14px; font-size: 13px; margin-bottom: 16px; background: #f8fafc; padding: 12px; border-radius: 8px; border: 1px solid #e2e8f0; }}
            .section-box {{ border-top: 1px solid #cbd5e1; padding: 12px 0; font-size: 13px; color: #334155; }}
            .advisory-box {{ border: 1px solid #0f172a; padding: 14px; margin: 16px 0; background-color: #f1f5f9; border-radius: 8px; font-size: 13px; color: #0f172a; }}
            .footer-signatures {{ display: flex; flex-wrap: wrap; justify-content: space-between; align-items: flex-end; gap: 16px; margin-top: 24px; font-size: 12px; }}
            .print-btn {{ display: block; width: 100%; max-width: 220px; margin: 0 auto 20px auto; padding: 10px; background-color: #0f172a; color: #ffffff; text-align: center; border-radius: 8px; cursor: pointer; font-weight: 600; font-size: 13px; border: none; }}
            @media print {{ .print-btn {{ display: none; }} body {{ padding: 0; }} .slip-card {{ border: 1px solid #000; padding: 15px; width: 100%; }} }}
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
                • <strong>Clinical Notes:</strong> {p.get('cbe_notes', 'None recorded')}<br>
                • <strong>BI-RADS Score:</strong> {p.get('birads_score', 'N/A')}<br>
                • <strong>POCUS:</strong> {'Orientation: ' + p['pocus_orientation'] + ' | Margins: ' + p['pocus_margins'] if p['pocus_available'] else 'Not Performed / Unavailable'}
            </div>
            <div class="section-box">
                <strong>2. CYTOLOGY & TELE-PATHOLOGY CHAIN OF CUSTODY</strong><br>
                • <strong>Procedure:</strong> {p['fnac_passes']}<br>
                • <strong>Slide Stained By:</strong> {p['prep_tech']} ({p['staining']}) | Macro Adequacy: {p['macro_adequate']}<br>
                • <strong>IAC Yokohama Category:</strong> <strong>{p['yokohama']}</strong><br>
                • <strong>Estimated Risk of Malignancy (ROM):</strong> <span style="color: #991b1b; font-weight: bold;">{p.get('yokohama_rom', 'N/A')}</span><br>
                • <strong>Robinson Cytological Grade:</strong> <span style="font-weight:bold;">{p.get('robinson_grade', 'N/A')} (Score: {p.get('robinson_score', 'N/A')}/18)</span><br>
                • <strong>Nottingham Histological Grade:</strong> <span style="font-weight:bold;">{p.get('nottingham_grade', 'N/A')} (Score: {p.get('nottingham_score', 'N/A')}/9)</span><br>
                • <strong>Pathologist Observations:</strong> {p['path_notes']}<br>
                • <strong>Reviewer:</strong> {p.get('pathologist','')}<br>
                {img_html}
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
            <div style="border-top: 1px solid #cbd5e1; margin-top: 20px; padding-top: 10px; text-align: center; font-size: 11px; font-weight: bold; color: #475569;">
                **NOT DIAGNOSTIC. Triage Advisory for Clinical Decision Support. Proceed to Confirmatory Histopathology.**
            </div>
        </div>
        </body>
        </html>
        """
        components.html(report_html, height=850, scrolling=True)

# =========================================================================
# MODULE 5: ASHA CLOSED-LOOP TRACKER
# =========================================================================
elif role == "5. ASHA Closed-Loop Tracker":
    with st.container(border=True):
        st.header(f"5. ASHA Community Follow-Up Tracking: {patient['name']}")
        st.caption("Monitor tertiary referral completion within the 21-day window to eliminate loss-to-follow-up.")

        col1, col2 = st.columns(2)
        with col1:
            patient["asha_worker"] = voice_text_input("ASHA Worker Name:", patient.get("asha_worker", ""), "asha_name_trk")
            patient["asha_contact"] = voice_text_input("ASHA Contact Number:", patient.get("asha_contact", ""), "asha_cont_trk")
            if patient.get("asha_contact"):
                alert_url = generate_whatsapp_link(patient["asha_contact"], patient["name"], patient["case_id"], patient.get("yokohama", ""), "Complete district hospital referral.")
                st.link_button("📲 Send Follow-Up Reminder via WhatsApp", alert_url)
        with col2:
            patient["tracker_status"] = st.selectbox("Status:", ["Referral Pending", "Appointment Scheduled", "Core Biopsy Completed"], index=0)
            st.date_input("Deadline (21 Days):", datetime.date.today() + datetime.timedelta(days=21))

# =========================================================================
# MODULE 6: PROVENANCE AUDIT TRAIL
# =========================================================================
elif role == "6. Audit Trail & Provenance (Who Did What)":
    with st.container(border=True):
        st.header(f"6. Clinical Audit Trail & Provenance: Case {patient['case_id']}")
        for log_item in patient.get("audit_log", []):
            st.code(log_item, language="markdown")

# =========================================================================
# MODULE 7: ADVANCED BATCH EXCEL VALIDATOR & RESEARCH ANALYTICS
# =========================================================================
elif role == "7. Advanced Batch Excel Validator & Analytics":
    with st.container(border=True):
        st.header("7. Advanced Batch Research Workbench & Excel Validator")
        uploaded_thesis_file = st.file_uploader("Upload Thesis Excel / CSV Dataset:", type=["xlsx", "xls", "csv"], key="batch_excel_uploader")

        if uploaded_thesis_file is not None:
            try:
                if uploaded_thesis_file.name.endswith(".csv"):
                    batch_df = pd.read_csv(uploaded_thesis_file)
                else:
                    batch_df = pd.read_excel(uploaded_thesis_file)

                if st.button("🚀 Run Batch CDSS Evaluation & Compute Metrics", type="primary"):
                    def evaluate_batch_row(row):
                        birads = str(row.get("Radio / BI-RADS", "")).upper().strip()
                        cyto = str(row.get("Cyto / FNAC", "")).lower().strip()
                        histo = str(row.get("Histo", "")).lower().strip()
                        
                        high_radio = any(b in birads for b in ["IV", "V", "4", "VI"])
                        is_malignant_cyto = "carcinoma" in cyto or "malignant" in cyto or "suspicious" in cyto
                        is_benign_cyto = "benign" in cyto or "fibroadenoma" in cyto or "cyst" in cyto
                        
                        mandate = True if (high_radio and is_benign_cyto) or high_radio or is_malignant_cyto else False
                        is_mal_histo = "carcinoma" in histo or "ca" in histo or "malignant" in histo
                        return mandate, is_mal_histo

                    eval_results = batch_df.apply(evaluate_batch_row, axis=1)
                    batch_df["CDSS_Mandated_Biopsy"] = [r[0] for r in eval_results]
                    batch_df["Histology_Malignant"] = [r[1] for r in eval_results]

                    tp = np.sum(batch_df["CDSS_Mandated_Biopsy"] & batch_df["Histology_Malignant"])
                    fn = np.sum(~batch_df["CDSS_Mandated_Biopsy"] & batch_df["Histology_Malignant"])
                    tn = np.sum(~batch_df["CDSS_Mandated_Biopsy"] & ~batch_df["Histology_Malignant"])
                    fp = np.sum(batch_df["CDSS_Mandated_Biopsy"] & ~batch_df["Histology_Malignant"])

                    sens = tp / (tp + fn) if (tp + fn) > 0 else 0
                    spec = tn / (tn + fp) if (tn + fp) > 0 else 0

                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("Total Cases", len(batch_df))
                    m2.metric("True Positives", tp)
                    m3.metric("False Negatives", fn)
                    m4.metric("Sensitivity", f"{sens * 100:.1f}%")

                    m5, m6 = st.columns(2)
                    m5.metric("Specificity", f"{spec * 100:.1f}%")
                    m6.metric("False Positives", fp)

                    st.dataframe(batch_df[["Case ID", "Patient Name", "Radio / BI-RADS", "Cyto / FNAC", "Histo"]], use_container_width=True)
            except Exception as e:
                st.error(f"Error processing uploaded file: {e}")