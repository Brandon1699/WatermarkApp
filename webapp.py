import streamlit as st
from PIL import Image, ImageOps
import io
import zipfile
import os

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Editor Móvil Pro", page_icon="📱", layout="centered")

# --- ESTILOS CSS ---
st.markdown("""
    <style>
    .stButton>button {
        width: 100%;
        border-radius: 12px;
        height: 3.5em;
        font-weight: bold;
    }
    /* Estilo especial para el botón de descarga individual */
    .download-btn {
        background-color: #4CAF50 !important;
        color: white !important;
    }
    </style>
""", unsafe_allow_html=True)

st.title("📱 Editor Móvil HD")

# --- VERIFICACIÓN DE LOGOS ---
if not os.path.exists("logo_negro.png") or not os.path.exists("logo_blanco.png"):
    st.error("⚠️ Faltan los archivos de logo.")
    st.stop()

logos = {
    "Negro": Image.open("logo_negro.png"),
    "Blanco": Image.open("logo_blanco.png")
}

# --- MEMORIA ---
if 'settings' not in st.session_state:
    st.session_state.settings = {} 
if 'current_index' not in st.session_state:
    st.session_state.current_index = 0

# --- FUNCIÓN DE PROCESADO ---
def aplicar_watermark(img_pil, color, opacidad, tamano):
    img = img_pil.copy()
    img = ImageOps.exif_transpose(img).convert("RGBA")
    w, h = img.size

    logo = logos[color].copy().convert("RGBA")

    # Opacidad
    if opacidad < 100:
        alpha = logo.split()[3]
        factor = opacidad / 100.0
        alpha = alpha.point(lambda p: int(p * factor))
        logo.putalpha(alpha)

    # Tamaño
    factor_tamano = tamano / 100.0
    ratio = logo.width / logo.height
    new_w = int(w * factor_tamano)
    new_h = int(new_w / ratio)
    
    if new_w < 1: new_w = 1
    if new_h < 1: new_h = 1
    
    logo_resized = logo.resize((new_w, new_h), Image.Resampling.LANCZOS)

    # Posición Centro
    x = (w - new_w) // 2
    y = (h - new_h) // 2

    img.paste(logo_resized, (x, y), logo_resized)
    return img.convert("RGB")

# --- INTERFAZ ---

uploaded_files = st.file_uploader("📂 Toca aquí para subir fotos", type=['jpg', 'jpeg', 'png'], accept_multiple_files=True)

if uploaded_files:
    # Validar índice
    total_imgs = len(uploaded_files)
    if st.session_state.current_index >= total_imgs:
        st.session_state.current_index = total_imgs - 1
    
    current_file = uploaded_files[st.session_state.current_index]
    file_id = current_file.name

    # Configuración por defecto (Tamaño 100, Opacidad 40)
    if file_id not in st.session_state.settings:
        st.session_state.settings[file_id] = {
            "color": "Blanco", 
            "opacidad": 40,
            "tamano": 100
        }

    current_conf = st.session_state.settings[file_id]

    # --- NAVEGACIÓN ---
    c_prev, c_txt, c_next = st.columns([1, 2, 1])
    with c_prev:
        if st.button("⬅️"):
            if st.session_state.current_index > 0:
                st.session_state.current_index -= 1
                st.rerun()
    with c_txt:
        st.markdown(f"<h3 style='text-align: center; margin:0'>{st.session_state.current_index + 1} / {total_imgs}</h3>", unsafe_allow_html=True)
    with c_next:
        if st.button("➡️"):
            if st.session_state.current_index < total_imgs - 1:
                st.session_state.current_index += 1
                st.rerun()

    st.markdown("---")

    # --- PREVIEW (Baja resolución para velocidad) ---
    img_original = Image.open(current_file)
    img_thumb = img_original.copy()
    img_thumb.thumbnail((600, 600)) # Solo para ver en pantalla
    
    img_preview = aplicar_watermark(
        img_thumb, 
        current_conf["color"], 
        current_conf["opacidad"], 
        current_conf["tamano"]
    )
    st.image(img_preview, use_column_width=True)

    # --- CONTROLES ---
    new_color = st.radio("Color", ["Blanco", "Negro"], index=0 if current_conf["color"] == "Blanco" else 1, horizontal=True)
    new_opacidad = st.slider("Opacidad (%)", 0, 100, current_conf["opacidad"])
    new_tamano = st.slider("Tamaño (%)", 10, 100, current_conf["tamano"])

    if (new_color != current_conf["color"] or 
        new_opacidad != current_conf["opacidad"] or 
        new_tamano != current_conf["tamano"]):
        st.session_state.settings[file_id] = {
            "color": new_color, "opacidad": new_opacidad, "tamano": new_tamano
        }
        st.rerun()

    st.markdown("---")

    # --- ZONA DE DESCARGA INDIVIDUAL ---
    # Procesamos la imagen ORIGINAL (Alta Calidad) en tiempo real para descargarla ya
    img_hd_final = aplicar_watermark(
        img_original, # Usamos la original, no el thumbnail
        current_conf["color"],
        current_conf["opacidad"],
        current_conf["tamano"]
    )
    
    # Convertimos a bytes para el botón de descarga
    buf = io.BytesIO()
    # CALIDAD MÁXIMA: quality=100, subsampling=0
    img_hd_final.save(buf, format="JPEG", quality=100, subsampling=0)
    byte_im = buf.getvalue()

    # Botón grande para descargar SOLO ESTA FOTO
    st.download_button(
        label="⬇️ DESCARGAR ESTA FOTO (HD)",
        data=byte_im,
        file_name=f"Logo_{current_file.name.split('.')[0]}.jpg",
        mime="image/jpeg",
        type="primary" # Lo hace destacar visualmente
    )

    # --- ZONA DE DESCARGA ZIP (Opcional, por si quieres todas) ---
    with st.expander("O descargar todas juntas (ZIP)"):
        if st.button("Generar ZIP de todas"):
            zip_buffer = io.BytesIO()
            barra = st.progress(0)
            with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
                for i, file in enumerate(uploaded_files):
                    conf = st.session_state.settings.get(file.name, {"color": "Blanco", "opacidad": 40, "tamano": 100})
                    orig = Image.open(file)
                    final = aplicar_watermark(orig, conf["color"], conf["opacidad"], conf["tamano"])
                    
                    b = io.BytesIO()
                    final.save(b, format="JPEG", quality=100, subsampling=0)
                    zip_file.writestr(f"Logo_{file.name}", b.getvalue())
                    barra.progress((i+1)/total_imgs)
            
            st.download_button("💾 Bajar ZIP", data=zip_buffer.getvalue(), file_name="fotos_todas.zip", mime="application/zip")
