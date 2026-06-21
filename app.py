import streamlit as st
import easyocr
import cv2
import numpy as np
import zipfile
import io
import os
import re

# 1. تحسين الأداء عبر تخزين النموذج في الذاكرة المؤقتة لمنع إعادة تحميله
@st.cache_resource
def load_ocr_reader():
    return easyocr.Reader(['en'], model_storage_directory='/tmp', gpu=False)

reader = load_ocr_reader()

# إعدادات الصفحة
st.set_page_config(page_title="مستخرج الأسماء الذكي", page_icon="📸", layout="wide")

st.title("📸 تطبيق إعادة تسمية الصور الذكي (OCR)")
st.subheader("قم برفع صورك، وسيقوم الذكاء الاصطناعي باستخراج الكود المناسب لتسمية الملف وضغطه.")
st.markdown("---")

# واجهة رفع الملفات
uploaded_files = st.file_uploader(
    "اختر الصور (JPG, JPEG, PNG)...", 
    accept_multiple_files=True, 
    type=['jpg', 'jpeg', 'png']
)

if uploaded_files and st.button("🚀 بدء المعالجة والتسمية الذكية", type="primary"):
    
    # استخدام BytesIO لإنشاء ملف ZIP في الذاكرة مباشرة دون الحاجة للكتابة على القرص
    zip_buffer = io.BytesIO()
    used_names = {}  # مصفوفة لتتبع الأسماء المكررة وتجنب استبدال الملفات
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # إنشاء حاوية لعرض النتائج بشكل منظم
        st.write("### 📊 نتائج المعالجة:")
        
        for idx, file in enumerate(uploaded_files):
            status_text.text(f"جاري معالجة: {file.name} ({idx+1}/{len(uploaded_files)})")
            
            # قراءة الملف
            file_bytes = file.read()
            nparr = np.frombuffer(file_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            # 2. معالجة تحضيرية للصورة لزيادة دقة الـ OCR
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            # تكبير الصورة قليلاً إذا كانت صغيرة جداً لتحسين القراءة
            if gray.shape[0] < 500 or gray.shape[1] < 500:
                gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
            
            # قراءة النص
            results = reader.readtext(gray)
            
            detected_name = None
            # البحث عن النمط المطلوب (ca متبوعاً بأرقام أو رموز)
            for (bbox, text, prob) in results:
                clean_text = text.strip()
                # البحث عن الكود عبر التعبير النمطي
                match = re.search(r'(?i)ca[\d_\-]+', clean_text)
                if match:
                    detected_name = match.group(0) # أخذ الجزء المطابق تماماً للنمط
                    break
            
            # في حال لم يتم العثور على النمط، يتم الاعتماد على الاسم الأصلي
            if not detected_name:
                detected_name = os.path.splitext(file.name)[0]
            
            # تنظيف الاسم من الرموز غير المسموحة في أنظمة التشغيل
            detected_name = re.sub(r'[\\/*?:"<>| ]', "_", detected_name)
            ext = os.path.splitext(file.name)[1].lower()
            
            # 4. حل مشكلة تكرار الأسماء
            if detected_name in used_names:
                used_names[detected_name] += 1
                final_filename = f"{detected_name}_{used_names[detected_name]}{ext}"
            else:
                used_names[detected_name] = 0
                final_filename = f"{detected_name}{ext}"
            
            # حفظ الملف في الـ ZIP بالذاكرة
            zipf.writestr(final_filename, file_bytes)
            
            # عرض النتيجة للمستخدم بطريقة منسقة
            col1, col2 = st.columns([1, 4])
            with col1:
                st.image(file_bytes, width=80)  # عرض مصغر للصورة للمعالجة البصرية
            with col2:
                st.success(f"الاسم الأصلي: `{file.name}` ➡️ الاسم الجديد: **{final_filename}**")
            
            # تحديث شريط التقدم
            progress_bar.progress((idx + 1) / len(uploaded_files))
            
        status_text.text("✨ اكتملت المعالجة بنجاح!")
        
    # إعادة مؤشر الـ BytesIO إلى الصفر ليكون جاهزاً للقراءة
    zip_buffer.seek(0)
    
    st.markdown("---")
    # 5. زر تحميل احترافي ومميز
    st.download_button(
        label="📥 تحميل ملف الصور المسمى ZIP",
        data=zip_buffer,
        file_name="renamed_site_images.zip",
        mime="application/zip",
        use_container_width=True
    )
