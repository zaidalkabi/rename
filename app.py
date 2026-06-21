import streamlit as st
import easyocr
import cv2
import numpy as np
import zipfile
import os
import re
import pandas as pd

# Page Configuration
st.set_page_config(page_title="Site Image Auto-Renamer", page_icon="📸", layout="wide")

# Custom CSS for Professional Dark/Modern Look
st.markdown("""
    <style>
    .main-title { font-size: 38px; font-weight: 700; color: #1E3A8A; text-align: center; margin-bottom: 10px; }
    .sub-title { font-size: 18px; color: #4B5563; text-align: center; margin-bottom: 30px; }
    .stButton>button { background-color: #2563EB; color: white; border-radius: 8px; font-weight: bold; width: 100%; padding: 10px; transition: 0.3s; }
    .stButton>button:hover { background-color: #1D4ED8; border-color: #1D4ED8; }
    .metric-card { background-color: #F3F4F6; padding: 15px; border-radius: 10px; text-align: center; border: 1px solid #E5E7EB; }
    </style>
""", unsafe_allow_html=True)

# Initialize EasyOCR with safe path for cloud hosting
@st.cache_resource
def load_ocr():
    return easyocr.Reader(['en'], model_storage_directory='/tmp')

reader = load_ocr()

# App Header
st.markdown("<div class='main-title'>📸 Smart Site Image Renamer</div>", unsafe_allow_html=True)
st.markdown("<div class='sub-title'>Advanced OCR tool to automatically detect site labels, rename files, and export to ZIP.</div>", unsafe_allow_html=True)

# File Uploader
uploaded_files = st.file_uploader("Drag and drop or upload your site images here", accept_multiple_files=True, type=['jpg', 'jpeg', 'png'])

if uploaded_files:
    # Quick Dashboard Metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"<div class='metric-card'>📁 <b>Total Files</b><br><span style='font-size:24px; color:#2563EB;'>{len(uploaded_files)}</span></div>", unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Process Button
    if st.button("🚀 Process & Extract Labels"):
        processed_data = []
        all_file_bytes = {}
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for idx, file in enumerate(uploaded_files):
            status_text.text(f"Analyzing image {idx+1}/{len(uploaded_files)}: {file.name}")
            
            # Read Image bytes
            file_bytes = file.read()
            all_file_bytes[file.name] = file_bytes
            
            # Convert to OpenCV format for enhancement
            nparr = np.frombuffer(file_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            # --- Advanced Image Preprocessing for Better OCR ---
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            # Resize if image is too small to improve OCR accuracy
            gray = cv2.resize(gray, None, fx=1.5, fy=1.5, interpolation=cv2.INTER_CUBIC)
            # Apply adaptive thresholding to make text pop out
           enhanced_img = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
            # Run EasyOCR on enhanced image
            results = reader.readtext(enhanced_img)
            
            # Fallback to original image if enhanced image returns nothing
            if not results:
                results = reader.readtext(img)
                
            detected_name = None
            confidence = 0
            
            # Regex pattern to match site codes like ca5_3, Ca3-3, ca7
            pattern = r'(?i)\bca[\d_\-]+\b'
            
            for (bbox, text, prob) in results:
                clean_text = text.strip().replace(" ", "") # Remove accidental spaces inside text
                match = re.search(pattern, clean_text)
                if match:
                    detected_name = match.group(0)
                    confidence = int(prob * 100)
                    break
            
            # If OCR fails to find the specific pattern, fall back to original name
            if not detected_name:
                detected_name = os.path.splitext(file.name)[0]
                status_type = "⚠️ No Label Found"
            else:
                status_type = "✅ Success"
                
            # Clean filename from any illegal characters
            detected_name = re.sub(r'[\\/*?:"<>|]', "", detected_name)
            ext = os.path.splitext(file.name)[1]
            
            processed_data.append({
                "Original Name": file.name,
                "Detected Label": detected_name,
                "Extension": ext,
                "Confidence": f"{confidence}%" if confidence > 0 else "N/A",
                "Status": status_type
            })
            
            progress_bar.progress((idx + 1) / len(uploaded_files))
            
        status_text.success("🎉 All images processed successfully!")
        
        # Save processed data to session state for management
        st.session_state['processed_df'] = pd.DataFrame(processed_data)
        st.session_state['all_file_bytes'] = all_file_bytes

    # --- Data Management Section ---
    if 'processed_df' in st.session_state:
        st.subheader("📊 Data Management Dashboard")
        st.write("Review and update the detected filenames below if needed before downloading.")
        
        # Display an editable data editor! User can manually overwrite names if OCR made a minor typo
        edited_df = st.data_editor(
            st.session_state['processed_df'],
            column_config={
                "Detected Label": st.column_config.TextColumn("New Filename (Editable)", help="Double click to edit manually if needed"),
                "Confidence": st.column_config.TextColumn("OCR Accuracy"),
                "Status": st.column_config.TextColumn("Status")
            },
            disabled=["Original Name", "Extension", "Confidence", "Status"],
            use_container_width=True
        )
        
        # Generate ZIP Button based on the final table data
        st.markdown("<br>", unsafe_allow_html=True)
        zip_path = "final_renamed_images.zip"
        
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for index, row in edited_df.iterrows():
                orig_name = row["Original Name"]
                final_label = row["Detected Label"]
                ext = row["Extension"]
                
                # Get the cached file bytes
                f_bytes = st.session_state['all_file_bytes'][orig_name]
                
                final_filename = f"{final_label}{ext}"
                zipf.writestr(final_filename, f_bytes)
                
        # Download Button
        with open(zip_path, "rb") as f:
            st.download_button(
                label="📥 Download All Renamed Images (ZIP)",
                data=f,
                file_name="renamed_site_images.zip",
                mime="application/zip"
            )
