"""فشرده‌سازی خودکار تصاویر محصول هنگام آپلود — تبدیل به WebP و کوچک‌کردن."""
import io

from django.core.files.base import ContentFile
from PIL import Image

MAX_SIDE = 1200   # حداکثر ضلع — کارت‌ها حداکثر ~۳۰۰px نمایش می‌دهند (رتینا ×۲ تا ۴)
MIN_SIDE = 900    # حداقل ضلع — ترب تصاویر زیر ۶۰۰px را نمایش نمی‌دهد و ۹۰۰×۹۰۰ را توصیه می‌کند
QUALITY = 82      # کیفیت WebP — تعادل حجم/کیفیت


def compress_product_image(uploaded_file):
    """یک فایل آپلودشده را به WebP (بین ۹۰۰ تا ۱۲۰۰px) تبدیل می‌کند و ContentFile برمی‌گرداند."""
    img = Image.open(uploaded_file)
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGBA" if "transparency" in img.info else "RGB")
    side = max(img.size)
    if side > MAX_SIDE or side < MIN_SIDE:
        ratio = (MAX_SIDE if side > MAX_SIDE else MIN_SIDE) / side
        img = img.resize(
            (round(img.width * ratio), round(img.height * ratio)),
            Image.LANCZOS,
        )
    buf = io.BytesIO()
    img.save(buf, "WEBP", quality=QUALITY, method=4)
    base = (getattr(uploaded_file, "name", "image") or "image").rsplit(".", 1)[0]
    return ContentFile(buf.getvalue(), name=f"{base}.webp")
