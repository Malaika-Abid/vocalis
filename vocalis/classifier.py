from typing import Tuple

def classify_speech_style(
    speaking_rate: float,
    articulation_rate: float,
    pause_ratio: float,
    pitch_var_label: str,
    energy_var_label: str,
) -> Tuple[str, str]:
    """
    Synthesize an intuitive speech style classification and coaching insight
    calibrated against acoustic prosody standards.
    """
    is_expressive = (pitch_var_label in ["Moderate", "High"] and energy_var_label == "High") or (pitch_var_label == "High")
    is_monotone = (pitch_var_label == "Low")

    # 1. Check for RUSHED speech first:
    # High articulation rate or speaking rate combined with inadequate pauses
    is_fast_pace = (articulation_rate >= 4.6 or speaking_rate >= 4.5)
    
    if is_fast_pace:
        if pause_ratio < 14.0:
            style = "Rushed / rapid delivery"
            desc = (
                f"Hurried tempo ({speaking_rate:.1f} syllables/sec) with minimal pauses ({int(round(pause_ratio))}%). "
                "Speaking continuously without pauses creates a breathless, rushed impression. "
                "Practice slowing your articulation and inserting deliberate 0.5s–1.0s pauses between key phrases."
            )
            return style, desc
        elif is_monotone:
            style = "Fast / monotone delivery"
            desc = (
                f"Rushing forward at {speaking_rate:.1f} syl/s with flat pitch inflection. "
                "Slow down at transitions and inject pitch lifts on key words to keep listeners engaged."
            )
            return style, desc
        elif pause_ratio >= 15.0 and is_expressive:
            style = "Brisk / expressive speech"
            desc = (
                f"Energetic and brisk tempo ({speaking_rate:.1f} syl/s) with healthy pauses. "
                "Lively for short pitches, but monitor speed so complex ideas have time to land."
            )
            return style, desc
        else:
            style = "Rapid / conversational delivery"
            desc = (
                f"Quick conversational tempo ({speaking_rate:.1f} syl/s). "
                "Consider adding slightly longer pauses before your main takeaways."
            )
            return style, desc

    # 2. Check for SLOW / DELIBERATE pace:
    is_slow_pace = (speaking_rate < 3.2 and articulation_rate < 3.8)
    if is_slow_pace:
        if is_monotone:
            style = "Slow / monotone delivery"
            desc = (
                f"Low tempo ({speaking_rate:.1f} syl/s) combined with flat intonation. "
                "Injecting more pitch inflection on key concepts will add vitality to your delivery."
            )
            return style, desc
        elif is_expressive or pause_ratio >= 20.0:
            style = "Deliberate / authoritative speech"
            desc = (
                f"Measured, deliberate pace ({speaking_rate:.1f} syl/s) with strong presence. "
                "Effective for keynotes and high-stakes announcements."
            )
            return style, desc
        else:
            style = "Slow / relaxed speech"
            desc = "Gentle, unhurried cadence. You can safely pick up the tempo slightly to build momentum."
            return style, desc

    # 3. Check for HESITANT / EXCESSIVE pauses:
    if pause_ratio > 32.0:
        style = "Hesitant / broken cadence"
        desc = (
            f"Pauses account for {int(round(pause_ratio))}% of speech time, breaking forward momentum. "
            "Practice linking related ideas together to maintain a steady conversational flow."
        )
        return style, desc

    # 4. BALANCED TEMPO (3.3 - 4.5 syl/s):
    if is_expressive:
        style = "Dynamic / engaging delivery"
        desc = (
            f"Well-balanced cadence ({speaking_rate:.1f} syl/s) with lively pitch and energy shifts. "
            "Natural and engaging rhythm that holds listener attention."
        )
    elif is_monotone:
        style = "Steady / flat delivery"
        desc = (
            f"Pacing is balanced ({speaking_rate:.1f} syl/s), but vocal inflection is relatively flat. "
            "Try emphasizing operative words with subtle pitch changes."
        )
    else:
        style = "Natural / conversational speech"
        desc = (
            f"Comfortable, everyday conversational rhythm ({speaking_rate:.1f} syl/s) with balanced pauses."
        )

    return style, desc
