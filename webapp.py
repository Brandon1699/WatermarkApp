import streamlit as st
from PIL import Image, ImageOps
import io
import zipfile
import os

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Editor Móvil de Watermark", page_icon="📱", layout="centered")

# --- ESTILOS CSS PARA MÓVIL ---
# Botones grandes para facilitar el toque en pantallas táctiles
st.markdown("""
    <style>
    .stButton>button {
        width: 100%;
        border-radius: 12px;
        height: 3.5em;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

st.title("📱 Editor Móvil Pro")

# --- VERIFICACIÓN DE LOGOS ---
if not os.path.exists("logo_negro.png") or not os.path.exists("logo_blanco.png"):
    st.error("⚠️ Faltan los archivos 'logo_negro.png' y 'logo_blanco.png'.")
    st.stop()

# Cargamos logos en memoria una sola vez
logos = {
    "Negro": Image.open("logo_negro.png"),
    "Blanco": Image.open("logo_blanco.png")
}

# --- GESTIÓN DE MEMORIA (SESSION STATE) ---
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

    # 1. Opacidad
    if opacidad < 100:
        alpha = logo.split()[3]
        factor = opacidad / 100.0
        alpha = alpha.point(lambda p: int(p * factor))
        logo.putalpha(alpha)

    # 2. Tamaño
    factor_tamano = tamano / 100.0
    ratio = logo.width / logo.height
    new_w = int(w * factor_tamano)
    new_h = int(new_w / ratio)
    
    # Evitar errores si el tamaño es muy pequeño
    if new_w < 1: new_w = 1
    if new_h < 1: new_h = 1
    
    logo_resized = logo.resize((new_w, new_h), Image.Resampling.LANCZOS)

    # 3. Posición (Siempre Centrado)
    x = (w - new_w) // 2
    y = (h - new_h) // 2

    img.paste(logo_resized, (x, y), logo_resized)
    return img.convert("RGB")

# --- INTERFAZ PRINCIPAL ---

uploaded_files = st.file_uploader("📂 Toca aquí para subir tus fotos", type=['jpg', 'jpeg', 'png'], accept_multiple_files=True)

if uploaded_files:
    # Control de índice para no pasarnos del límite
    total_imgs = len(uploaded_files)
    if st.session_state.current_index >= total_imgs:
        st.session_state.current_index = total_imgs - 1
    
    current_file = uploaded_files[st.session_state.current_index]
    file_id = current_file.name

    # --- CONFIGURACIÓN POR DEFECTO ---
    # Aquí es donde hemos cambiado el valor a 100
    if file_id not in st.session_state.settings:
        st.session_state.settings[file_id] = {
            "color": "Blanco", 
            "opacidad": 40,   # Opacidad inicial
            "tamano": 100     # Tamaño inicial al 100%
        }

    # Recuperamos la configuración de la foto actual
    current_conf = st.session_state.settings[file_id]

    # --- BOTONES DE NAVEGACIÓN ---
    c_prev, c_txt, c_next = st.columns([1, 2, 1])
    
    with c_prev:
        if st.button("⬅️ Atrás"):
            if st.session_state.current_index > 0:
                st.session_state.current_index -= 1
                st.rerun()
    
    with c_txt:
        st.markdown(f"<h3 style='text-align: center; margin:0'>{st.session_state.current_index + 1} / {total_imgs}</h3>", unsafe_allow_html=True)
        st.caption(f"Editando: {current_file.name}")

    with c_next:
        if st.button("Sig ➡️"):
            if st.session_state.current_index < total_imgs - 1:
                st.session_state.current_index += 1
                st.rerun()

    st.markdown("---")

    # --- PREVIEW IMAGEN ---
    # Usamos un thumbnail para que vaya rápido en el móvil
    img_original = Image.open(current_file)
    img_thumb = img_original.copy()
    img_thumb.thumbnail((600, 600))
    
    img_processed = aplicar_watermark(
        img_thumb, 
        current_conf["color"], 
        current_conf["opacidad"], 
        current_conf["tamano"]
    )
    st.image(img_processed, use_column_width=True)

    # --- CONTROLES DESLIZANTES ---
    st.info("Ajusta esta foto:")
    
    # 1. Color
    new_color = st.radio(
        "Color del Logo", 
        ["Blanco", "Negro"], 
        index=0 if current_conf["color"] == "Blanco" else 1,
        horizontal=True
    )
    
    # 2. Opacidad
    new_opacidad = st.slider("Opacidad (%)", 0, 100, current_conf["opacidad"])
    
    # 3. Tamaño
    new_tamano = st.slider("Tamaño (%)", 10, 100, current_conf["tamano"])

    # --- GUARDADO AUTOMÁTICO ---
    # Si detectamos cambios, actualizamos la memoria y recargamos
    if (new_color != current_conf["color"] or 
        new_opacidad != current_conf["opacidad"] or 
        new_tamano != current_conf["tamano"]):
        
        st.session_state.settings[file_id] = {
            "color": new_color,
            "opacidad": new_opacidad,
            "tamano": new_tamano
        }
        st.rerun()

    st.markdown("---")

    # --- ZONA DE DESCARGA ---
    if st.button("✅ TERMINAR Y DESCARGAR ZIP", type="primary"):
        
        zip_buffer = io.BytesIO()
        barra = st.progress(0)
        status = st.empty()
        
        with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
            for i, file in enumerate(uploaded_files):
                status.text(f"Procesando {i+1} de {total_imgs}...")
                
                # Usamos la config guardada o el default (100% tamaño, 40% opacidad)
                conf = st.session_state.settings.get(file.name, {
                    "color": "Blanco", "opacidad": 40, "tamano": 100
                })
                
                # Procesamos la imagen original en alta calidad
                original = Image.open(file)
                final = aplicar_watermark(original, conf["color"], conf["opacidad"], conf["tamano"])
                
                # Guardamos
                img_bytes = io.BytesIO()
                final.save(img_bytes, format="JPEG", quality=95)
                zip_file.writestr(f"Logo_{file.name}", img_bytes.getvalue())
                
                barra.progress((i + 1) / total_imgs)
        
        status.success("¡Completado!")
        st.download_button(
            "⬇️ Descargar Archivo ZIP", 
            data=zip_buffer.getvalue(), 
            file_name="fotos_listas.zip", 
            mime="application/zip"
        )