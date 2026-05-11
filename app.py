import streamlit as st
from PIL import Image, ImageFilter, ImageEnhance, ImageDraw, ImageFont
import io
import math
import zipfile
from pypdf import PdfWriter, PdfReader

# Optional deps handled safely
try:
    from rembg import remove as rembg_remove

    REMBG_OK = True
except ImportError:
    REMBG_OK = False


# --- Helper Functions ---
def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def load_img(uploaded_file):
    img = Image.open(uploaded_file)
    if getattr(img, "format", None) in ("GIF", "ICO") and img.mode != "RGBA":
        img = img.convert("RGBA")
    return img


def create_download_zip(file_dict, zip_filename="processed_files.zip"):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for filename, file_bytes in file_dict.items():
            zf.writestr(filename, file_bytes.getvalue())
    return buf.getvalue()


# --- App Config ---
st.set_page_config(page_title="Image Toolkit Web", page_icon="🖼", layout="centered")

st.sidebar.title("🖼 Image Toolkit")
tool = st.sidebar.radio("Select a Tool:", [
    "🎨 White Background",
    "📐 Resize Image",
    "✨ Upscale Image",
    "🗜 Compress Files",
    "🔗 Combine Images",
    "📄 Convert to PDF"
])

# ═══════════════════════════════════════════════════════════════════════════════
# 1. WHITE BACKGROUND
# ═══════════════════════════════════════════════════════════════════════════════
if tool == "🎨 White Background":
    st.header("🎨 White Background")
    st.write("AI-powered background removal — replace with any colour")

    if not REMBG_OK:
        st.error("rembg is not installed. Please install it via requirements.txt.")
    else:
        uploaded_files = st.file_uploader("Upload Images", type=["png", "jpg", "jpeg", "webp"],
                                          accept_multiple_files=True)
        bg_color = st.color_picker("Pick New Background Color", "#FFFFFF")

        if uploaded_files and st.button("Apply Background"):
            with st.spinner("Processing with AI..."):
                processed_files = {}
                for file in uploaded_files:
                    img = load_img(file)
                    buf = io.BytesIO()
                    img.save(buf, format="PNG")
                    buf.seek(0)

                    # Remove BG
                    removed = Image.open(io.BytesIO(rembg_remove(buf.read()))).convert("RGBA")

                    # Create new BG
                    bg = Image.new("RGBA", removed.size, hex_to_rgb(bg_color) + (255,))
                    bg.paste(removed, mask=removed.split()[3])
                    out = bg.convert("RGB")

                    out_buf = io.BytesIO()
                    out.save(out_buf, format="PNG")
                    processed_files[f"bg_{file.name.split('.')[0]}.png"] = out_buf

                if len(processed_files) == 1:
                    filename, buf = list(processed_files.items())[0]
                    st.download_button("⬇️ Download Image", buf.getvalue(), filename, "image/png")
                elif len(processed_files) > 1:
                    zip_data = create_download_zip(processed_files, "backgrounds.zip")
                    st.download_button("⬇️ Download All (ZIP)", zip_data, "backgrounds.zip", "application/zip")

# ═══════════════════════════════════════════════════════════════════════════════
# 2. RESIZE
# ═══════════════════════════════════════════════════════════════════════════════
elif tool == "📐 Resize Image":
    st.header("📐 Resize Image")
    file = st.file_uploader("Upload Image", type=["png", "jpg", "jpeg", "webp"])

    if file:
        img = load_img(file)
        st.write(f"**Original Size:** {img.width} x {img.height} px")

        mode = st.radio("Resize Mode", ["Pixels", "Extend Canvas"])

        if mode == "Pixels":
            col1, col2 = st.columns(2)
            with col1:
                nw = st.number_input("Width (px)", value=img.width, min_value=1)
            with col2:
                nh = st.number_input("Height (px)", value=img.height, min_value=1)

            if st.button("Resize"):
                result = img.resize((int(nw), int(nh)), Image.LANCZOS)
                buf = io.BytesIO()
                result.save(buf, format="PNG")
                st.download_button("⬇️ Download Resized", buf.getvalue(), f"resized_{file.name}", "image/png")

        elif mode == "Extend Canvas":
            col1, col2 = st.columns(2)
            with col1:
                cw = st.number_input("Canvas Width (px)", value=max(2000, img.width))
            with col2:
                ch = st.number_input("Canvas Height (px)", value=max(2000, img.height))
            ext_color = st.color_picker("Fill Color", "#FFFFFF")

            if st.button("Extend"):
                fill = hex_to_rgb(ext_color)
                canvas = Image.new("RGB", (int(cw), int(ch)), fill)
                cx, cy = (int(cw) - img.width) // 2, (int(ch) - img.height) // 2

                if img.mode == "RGBA":
                    canvas.paste(img, (cx, cy), mask=img.split()[3])
                else:
                    canvas.paste(img.convert("RGB"), (cx, cy))

                buf = io.BytesIO()
                canvas.save(buf, format="PNG")
                st.download_button("⬇️ Download Extended", buf.getvalue(), f"extended_{file.name}", "image/png")

# ═══════════════════════════════════════════════════════════════════════════════
# 3. UPSCALE
# ═══════════════════════════════════════════════════════════════════════════════
elif tool == "✨ Upscale Image":
    st.header("✨ Upscale Image")
    file = st.file_uploader("Upload Image", type=["png", "jpg", "jpeg", "webp"])

    if file:
        img = load_img(file)
        st.write(f"**Original Size:** {img.width} x {img.height} px")

        scale = st.slider("Scale Multiplier", 2, 4, 2)
        sharp = st.slider("Sharpening", 0, 200, 80)
        detail = st.slider("Detail Boost", 0, 100, 40)

        if st.button("Upscale"):
            with st.spinner("Upscaling..."):
                nw, nh = img.width * scale, img.height * scale
                up = (img if img.mode == "RGBA" else img.convert("RGB")).resize((nw, nh), Image.LANCZOS)

                if sharp > 0:
                    up = up.filter(ImageFilter.UnsharpMask(radius=1.5, percent=sharp, threshold=3))
                if detail > 0:
                    up = ImageEnhance.Contrast(up).enhance(1 + detail * 0.003)
                    up = up.filter(ImageFilter.UnsharpMask(radius=0.6, percent=detail, threshold=2))

                buf = io.BytesIO()
                up.save(buf, format="PNG")
                st.success(f"Upscaled to {nw} x {nh} px!")
                st.download_button("⬇️ Download Upscaled", buf.getvalue(), f"upscaled_{file.name}.png", "image/png")

# ═══════════════════════════════════════════════════════════════════════════════
# 4. COMPRESS
# ═══════════════════════════════════════════════════════════════════════════════
elif tool == "🗜 Compress Files":
    st.header("🗜 Compress Images & PDFs")
    files = st.file_uploader("Upload Files", type=["png", "jpg", "jpeg", "webp", "pdf"], accept_multiple_files=True)
    quality = st.slider("Quality (for images)", 10, 95, 75)

    if files and st.button("Compress"):
        with st.spinner("Compressing..."):
            processed = {}
            for f in files:
                ext = f.name.split('.')[-1].lower()
                buf = io.BytesIO()

                if ext == "pdf":
                    reader = PdfReader(f)
                    writer = PdfWriter()
                    for page in reader.pages:
                        page.compress_content_streams()
                        writer.add_page(page)
                    writer.write(buf)
                    processed[f"compressed_{f.name}"] = buf
                else:
                    img = load_img(f)
                    if img.mode in ("RGBA", "P"):
                        img = img.convert("RGB")
                    img.save(buf, format="JPEG", quality=quality, optimize=True)
                    processed[f"compressed_{f.name.split('.')[0]}.jpg"] = buf

            if len(processed) == 1:
                filename, out_buf = list(processed.items())[0]
                mime = "application/pdf" if "pdf" in filename else "image/jpeg"
                st.download_button("⬇️ Download", out_buf.getvalue(), filename, mime)
            else:
                zip_data = create_download_zip(processed, "compressed.zip")
                st.download_button("⬇️ Download All (ZIP)", zip_data, "compressed.zip", "application/zip")

# ═══════════════════════════════════════════════════════════════════════════════
# 5. COMBINE IMAGES
# ═══════════════════════════════════════════════════════════════════════════════
elif tool == "🔗 Combine Images":
    st.header("🔗 Combine Images")
    files = st.file_uploader("Upload Images", type=["png", "jpg", "jpeg", "webp"], accept_multiple_files=True)

    if files and len(files) >= 2:
        layout = st.radio("Layout", ["Horizontal", "Vertical", "Grid"])
        gap = st.number_input("Gap (px)", value=10, min_value=0)
        fill_color = st.color_picker("Gap/Fill Color", "#FFFFFF")

        if st.button("Combine"):
            images = [load_img(f).convert("RGBA") for f in files]
            fill = hex_to_rgb(fill_color) + (255,)

            if layout == "Horizontal":
                th = min(img.height for img in images)
                imgs = [img.resize((round(img.width * th / img.height), th), Image.LANCZOS) for img in images]
                tw = sum(i.width for i in imgs) + gap * (len(imgs) - 1)
                canvas = Image.new("RGBA", (tw, th), fill)
                x = 0
                for img in imgs:
                    canvas.paste(img, (x, 0))
                    x += img.width + gap

            elif layout == "Vertical":
                tw = min(img.width for img in images)
                imgs = [img.resize((tw, round(img.height * tw / img.width)), Image.LANCZOS) for img in images]
                th = sum(i.height for i in imgs) + gap * (len(imgs) - 1)
                canvas = Image.new("RGBA", (tw, th), fill)
                y = 0
                for img in imgs:
                    canvas.paste(img, (0, y))
                    y += img.height + gap

            else:  # Grid
                cols = math.ceil(math.sqrt(len(images)))
                rows = math.ceil(len(images) / cols)
                cw = max(img.width for img in images)
                ch = max(img.height for img in images)
                tw = cols * cw + (cols - 1) * gap
                th = rows * ch + (rows - 1) * gap
                canvas = Image.new("RGBA", (tw, th), fill)
                for idx, img in enumerate(images):
                    r, c = divmod(idx, cols)
                    x = c * (cw + gap) + (cw - img.width) // 2
                    y = r * (ch + gap) + (ch - img.height) // 2
                    canvas.paste(img, (x, y), mask=img.split()[3] if img.mode == "RGBA" else None)

            out = canvas.convert("RGB")
            buf = io.BytesIO()
            out.save(buf, format="PNG")
            st.image(out, caption="Preview", use_container_width=True)
            st.download_button("⬇️ Download Combined Image", buf.getvalue(), "combined.png", "image/png")

# ═══════════════════════════════════════════════════════════════════════════════
# 6. CONVERT TO PDF
# ═══════════════════════════════════════════════════════════════════════════════
elif tool == "📄 Convert to PDF":
    st.header("📄 Convert Images to PDF")
    files = st.file_uploader("Upload Images", type=["png", "jpg", "jpeg", "webp"], accept_multiple_files=True)

    if files and st.button("Generate PDF"):
        with st.spinner("Building PDF..."):
            pages = []
            for f in files:
                img = load_img(f)
                if img.mode in ("RGBA", "P", "LA"):
                    bg = Image.new("RGB", img.size, (255, 255, 255))
                    if img.mode == "RGBA":
                        bg.paste(img, mask=img.split()[3])
                    else:
                        rgba = img.convert("RGBA")
                        bg.paste(rgba, mask=rgba.split()[3])
                    img = bg
                elif img.mode != "RGB":
                    img = img.convert("RGB")
                pages.append(img)

            if pages:
                buf = io.BytesIO()
                pages[0].save(buf, "PDF", save_all=True, append_images=pages[1:], resolution=300)
                st.download_button("⬇️ Download PDF", buf.getvalue(), "converted.pdf", "application/pdf")