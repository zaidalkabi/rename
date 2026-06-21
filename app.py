import streamlit as st
import easyocr
import cv2
import numpy as np
import zipfile
import os
import re

# إعداد قارئ النصوص (يدعم الإنجليزية)
reader = easyocr.Reader(['en'], model_storage_directory='/tmp')

st.title("تطبيق إعادة تسمية الصور التلقائي")
st.write("ارفع صورك هنا، وسيقوم التطبيق بقراءة التسمية وضغطها في ملف ZIP")

uploaded_files = st.file_uploader("اختر الصور...", accept_multiple_files=True, type=['jpg', 'jpeg', 'png'])

if uploaded_files and st.button("بدء المعالجة والتسمية"):
    zip_path = "renamed_images.zip"
    
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        progress_bar = st.progress(0)
        
        for idx, file in enumerate(uploaded_files):
            # تحويل الملف المرفوع إلى مصفوفة صور لقراءتها
            file_bytes = np.frombuffer(file.read(), np.uint8)
            img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
            
            # قراءة النص من الصورة
            results = reader.readtext(img)
            
            # البحث عن التسمية المستهدفة (مثل ca5_3 أو Ca3-3)
            detected_name = None
            for (bbox, text, prob) in results:
                clean_text = text.strip()
                # تعبير نمطي للبحث عن الكلمات التي تبدأ بـ ca تليها أرقام أو رموز
                if re.search(r'(?i)ca[\d_\-]+', clean_text):
                    detected_name = clean_text
                    break
            
            # إذا لم يجد التسمية، يحتفظ بالاسم الأصلي منعاً للضياع
            if not detected_name:
                detected_name = os.path.splitext(file.name)[0]
                
            # تنظيف الاسم من أي رموز غير مسموحة في الملفات
            detected_name = re.sub(r'[\\/*?:"<>|]', "", detected_name)
            ext = os.path.splitext(file.name)[1]
            final_filename = f"{detected_name}{ext}"
            
            # حفظ الصورة داخل ملف الـ ZIP
            zipf.writestr(final_filename, file_bytes)
            st.write(f" تم التعرف والتسمية: **{final_filename}**")
            
            # تحديث شريط التقدم
            progress_bar.progress((idx + 1) / len(uploaded_files))
            
    # زر تحميل الملف المضغوط بعد الانتهاء
    with open(zip_path, "rb") as f:
        st.download_button(
            label="تحميل جميع الصور بملف مضغوط ZIP",
            data=f,
            file_name="renamed_site_images.zip",
            mime="application/zip"
        )
