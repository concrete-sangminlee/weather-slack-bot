"""동적 날씨 배지 SVG 생성기 — README에 현재 날씨 표시"""
from pathlib import Path

from config_loader import CITY_NAME
from weather_bot import extract_conditions, fetch_weather

BADGE_COLORS = {
    "A+": "2ecc71", "A": "27ae60", "B+": "3498db", "B": "2980b9",
    "C+": "f1c40f", "C": "e67e22", "D": "e74c3c", "F": "8e44ad",
}

SVG_TEMPLATE = """<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="20">
  <linearGradient id="a" x2="0" y2="100%">
    <stop offset="0" stop-color="#bbb" stop-opacity=".1"/>
    <stop offset="1" stop-opacity=".1"/>
  </linearGradient>
  <clipPath id="r"><rect width="{width}" height="20" rx="3" fill="#fff"/></clipPath>
  <g clip-path="url(#r)">
    <rect width="{label_w}" height="20" fill="#555"/>
    <rect x="{label_w}" width="{value_w}" height="20" fill="#{color}"/>
    <rect width="{width}" height="20" fill="url(#a)"/>
  </g>
  <g fill="#fff" text-anchor="middle" font-family="Verdana,Geneva,sans-serif" font-size="11">
    <text x="{label_x}" y="15" fill="#010101" fill-opacity=".3">{label}</text>
    <text x="{label_x}" y="14">{label}</text>
    <text x="{value_x}" y="15" fill="#010101" fill-opacity=".3">{value}</text>
    <text x="{value_x}" y="14">{value}</text>
  </g>
</svg>"""


def generate_badge() -> str:
    cond = extract_conditions(fetch_weather())
    grade = cond.grade

    label = CITY_NAME
    value = f"{cond.weather} {cond.temp}°C ({grade})"

    label_w = len(label) * 7 + 12
    value_w = len(value) * 6.5 + 12
    width = label_w + value_w
    color = BADGE_COLORS.get(grade, "555")

    svg = SVG_TEMPLATE.format(
        width=int(width), label_w=int(label_w), value_w=int(value_w),
        label_x=int(label_w / 2), value_x=int(label_w + value_w / 2),
        label=label, value=value, color=color,
    )

    badge_path = Path(__file__).parent / "docs" / "badge.svg"
    badge_path.write_text(svg, encoding="utf-8")
    return str(badge_path)


def main():
    path = generate_badge()
    print(f"Badge saved: {path}")


if __name__ == "__main__":
    main()
