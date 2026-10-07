"""
apps/publisher/video/music.py
──────────────────────────────
انتخاب موزیک پس‌زمینه برای ویدیو — موزیک دستی پست در اولویت است، وگرنه LLM
حال‌وهوای محتوا را حدس می‌زند و نزدیک‌ترین تراک فعال برگردانده می‌شود؛
در هر خطایی انتخاب تصادفی و در نبود تراک فعال None (ویدیو بدون صدا رندر می‌شود).
"""

import random

from ..models import MusicTrack

_MOOD_PROMPT = """تو دستیار تولید ویدیوی فروشگاه «دوربین‌کار» هستی. بر اساس عنوان و متن محتوا، فقط یکی از حال‌وهواهای داده‌شده را انتخاب کن.
خروجی فقط و فقط همان یک کلمهٔ حال‌وهوا باشد — بدون توضیح، نقل‌قول یا علامت اضافه."""


def _pick_mood(post, moods: list) -> str | None:
    """با LLM یک mood از میان moodهای موجود انتخاب می‌کند؛ در خطا None."""
    from apps.assistant.engine import ask_llm

    user = (
        f"عنوان محتوا: {post.title}\n"
        f"متن: {(post.body or '')[:400]}\n"
        f"نوع: {post.get_content_type_display()}\n"
        f"حال‌وهواهای موجود: {', '.join(moods)}"
    )
    raw, _engine = ask_llm(
        [{"role": "system", "content": _MOOD_PROMPT}, {"role": "user", "content": user}],
        max_tokens=50,
    )
    answer = raw.strip().strip('"\'`.,،').split()[0].lower() if raw.strip() else ""
    for mood in moods:
        if mood.lower() == answer:
            return mood
    return None


def pick_track(post) -> MusicTrack | None:
    """تراک مناسب پست را برمی‌گرداند؛ None یعنی ویدیو بدون صدا رندر شود."""
    if post.music_track_id:
        return post.music_track

    tracks = list(MusicTrack.objects.filter(is_active=True))
    if not tracks:
        return None

    moods = sorted({t.mood.strip() for t in tracks if t.mood and t.mood.strip()})
    if moods:
        try:
            mood = _pick_mood(post, moods)
        except Exception:
            mood = None
        if mood:
            matching = [t for t in tracks if t.mood.strip().lower() == mood.lower()]
            if matching:
                return random.choice(matching)

    return random.choice(tracks)
