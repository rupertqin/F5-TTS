from __future__ import annotations

import re

def remove_voice_markers(text: str) -> str:
    return re.sub(r"\[[^\]]+\]", "", text).strip()
