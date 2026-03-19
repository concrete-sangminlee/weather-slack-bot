#!/usr/bin/env python3
"""Seoul Weather Slack Bot — Unified CLI

Usage:
    weather-bot daily              # Full daily briefing
    weather-bot daily --dry-run    # Preview without sending
    weather-bot digest             # Short 1-block summary
    weather-bot weekly             # Weekly summary
    weather-bot alert              # Extreme weather check
    weather-bot chart              # Generate trend chart
    weather-bot version            # Version info
"""
import argparse


def cmd_daily(dry_run=False):
    from weather_bot import (
        build_blocks,
        build_fallback_text,
        fetch_air_quality,
        fetch_weather,
        send_to_slack,
    )

    data = fetch_weather()
    try:
        air_data = fetch_air_quality()
    except Exception:
        air_data = None

    blocks, color, weather_cat = build_blocks(data, air_data)
    fallback = build_fallback_text(data)

    if dry_run:
        print("=== DRY RUN (not sending to Slack) ===")
        print(f"Fallback: {fallback}")
        print(f"Color: {color}")
        print(f"Blocks: {len(blocks)}")
        for b in blocks:
            text = b.get("text", {})
            if isinstance(text, dict):
                t = text.get("text", "")
            else:
                t = ""
            fields = b.get("fields", [])
            elems = b.get("elements", [])
            if t:
                print(f"  [{b['type']}] {t[:100]}")
            for f in fields:
                print(f"    {f['text'][:60]}")
            for e in elems:
                print(f"    ctx: {e.get('text', '')[:80]}")
    else:
        chart_path = None
        try:
            from chart import generate_chart
            chart_path = generate_chart()
        except Exception:
            pass
        send_to_slack(blocks, fallback, chart_path, color)
        if chart_path:
            import os
            try:
                os.unlink(chart_path)
            except OSError:
                pass
        print("날씨 메시지 전송 완료!")


def cmd_digest(dry_run=False):
    """초단축 다이제스트 — 핵심 정보만 1블록으로"""
    from slack_sdk import WebClient

    from weather_bot import (
        CITY_NAME,
        SLACK_BOT_TOKEN,
        WEATHER_EMOJIS,
        WMO_DESCRIPTIONS,
        _get_channels,
        calc_lifestyle_index,
        fetch_air_quality,
        fetch_weather,
        get_outfit_recommendation,
        kmh_to_ms,
        weather_grade,
    )

    data = fetch_weather()
    cur = data["current"]
    daily = data["daily"]
    from weather_bot import PAST_DAYS
    idx = PAST_DAYS

    temp = cur["temperature_2m"]
    feels = cur["apparent_temperature"]
    hum = cur["relative_humidity_2m"]
    wind = kmh_to_ms(cur["wind_speed_10m"])
    code = cur["weather_code"]
    desc, cat = WMO_DESCRIPTIONS.get(code, ("?", "Clear"))
    emoji = WEATHER_EMOJIS.get(cat, "🌡️")
    t_max = daily["temperature_2m_max"][idx]
    t_min = daily["temperature_2m_min"][idx]
    prob = daily["precipitation_probability_max"][idx]

    aqi_text = ""
    try:
        air = fetch_air_quality()
        aqi = air["current"].get("us_aqi")
        aqi_text = f" · AQI {aqi}"
    except Exception:
        aqi = None

    score = calc_lifestyle_index(temp, hum, wind, None, aqi, prob)
    grade, color = weather_grade(score)
    outfit = get_outfit_recommendation(temp, feels, cat, prob)

    text = (
        f"{emoji} *{CITY_NAME}* {desc} *{temp}°C* (체감 {feels}°C)\n"
        f"⬆️{t_max}° ⬇️{t_min}° · 💧{hum}% · 🌬️{wind}m/s · ☔{prob}%{aqi_text}\n"
        f"등급 *{grade}* · {outfit}"
    )

    if dry_run:
        print("=== DIGEST DRY RUN ===")
        print(text)
    else:
        client = WebClient(token=SLACK_BOT_TOKEN)
        for ch in _get_channels():
            client.chat_postMessage(
                channel=ch,
                text=f"{CITY_NAME}: {desc} {temp}°C",
                attachments=[{
                    "color": color,
                    "blocks": [{"type": "section", "text": {"type": "mrkdwn", "text": text}}],
                }],
            )
        print("다이제스트 전송 완료!")


def cmd_weekly():
    from weekly_summary import main
    main()


def cmd_alert():
    from alert import main
    main()


def cmd_export():
    """날씨 데이터를 마크다운으로 출력"""
    from datetime import datetime

    from weather_bot import (
        CITY_NAME,
        PAST_DAYS,
        WMO_DESCRIPTIONS,
        calc_discomfort_index,
        calc_lifestyle_index,
        fetch_air_quality,
        fetch_weather,
        format_time,
        get_outfit_recommendation,
        kmh_to_ms,
        weather_grade,
    )

    data = fetch_weather()
    cur = data["current"]
    daily = data["daily"]
    idx = PAST_DAYS

    temp = cur["temperature_2m"]
    feels = cur["apparent_temperature"]
    hum = cur["relative_humidity_2m"]
    wind = kmh_to_ms(cur["wind_speed_10m"])
    code = cur["weather_code"]
    desc, cat = WMO_DESCRIPTIONS.get(code, ("?", "Clear"))
    t_max = daily["temperature_2m_max"][idx]
    t_min = daily["temperature_2m_min"][idx]
    prob = daily["precipitation_probability_max"][idx]
    sunrise = format_time(daily["sunrise"][idx])
    sunset = format_time(daily["sunset"][idx])

    aqi = pm25 = None
    try:
        air = fetch_air_quality()
        aqi = air["current"].get("us_aqi")
        pm25 = air["current"].get("pm2_5")
    except Exception:
        pass

    score = calc_lifestyle_index(temp, hum, wind, None, aqi, prob)
    grade, _ = weather_grade(score)
    di = calc_discomfort_index(temp, hum)
    outfit = get_outfit_recommendation(temp, feels, cat, prob)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    md = f"""# {CITY_NAME} Weather Report
> {now}

## Current Conditions
| Metric | Value |
|--------|-------|
| Weather | {desc} |
| Temperature | {temp}°C (feels {feels}°C) |
| High / Low | {t_max}°C / {t_min}°C |
| Humidity | {hum}% |
| Wind | {wind} m/s |
| Precipitation | {prob}% |
| Sunrise / Sunset | {sunrise} / {sunset} |
| AQI | {aqi or 'N/A'} |
| PM2.5 | {pm25 or 'N/A'} µg/m³ |

## Indices
| Index | Value |
|-------|-------|
| Lifestyle Score | {score}/100 (Grade {grade}) |
| Discomfort Index | {di} |

## Recommendation
- **Outfit**: {outfit}

---
*Generated by weather-slack-bot*
"""
    print(md)


def cmd_history():
    """히스토리에 오늘 데이터 저장 + 통계 출력"""
    from history import main
    main()


def cmd_json():
    """날씨 데이터를 JSON으로 출력"""
    import json as json_mod

    from weather_bot import (
        PAST_DAYS,
        WMO_DESCRIPTIONS,
        calc_discomfort_index,
        calc_lifestyle_index,
        fetch_air_quality,
        fetch_weather,
        kmh_to_ms,
        weather_grade,
    )

    data = fetch_weather()
    cur = data["current"]
    daily = data["daily"]
    idx = PAST_DAYS

    code = cur["weather_code"]
    desc, _ = WMO_DESCRIPTIONS.get(code, ("?", "Clear"))

    aqi = pm25 = None
    try:
        air = fetch_air_quality()
        aqi = air["current"].get("us_aqi")
        pm25 = air["current"].get("pm2_5")
    except Exception:
        pass

    temp = cur["temperature_2m"]
    hum = cur["relative_humidity_2m"]
    wind = kmh_to_ms(cur["wind_speed_10m"])
    prob = daily["precipitation_probability_max"][idx]
    score = calc_lifestyle_index(temp, hum, wind, None, aqi, prob)
    grade, color = weather_grade(score)

    output = {
        "timestamp": cur["time"],
        "weather": desc,
        "temperature": {"current": temp, "feels_like": cur["apparent_temperature"],
                        "max": daily["temperature_2m_max"][idx], "min": daily["temperature_2m_min"][idx]},
        "humidity": hum,
        "wind": {"speed_ms": wind, "gust_ms": kmh_to_ms(cur["wind_gusts_10m"])},
        "precipitation": {"probability": prob, "sum_mm": daily["precipitation_sum"][idx]},
        "air_quality": {"aqi": aqi, "pm25": pm25},
        "indices": {"lifestyle": score, "grade": grade, "discomfort": calc_discomfort_index(temp, hum)},
    }
    print(json_mod.dumps(output, ensure_ascii=False, indent=2))


def cmd_chart():
    from chart import generate_chart
    path = generate_chart()
    print(f"Chart saved: {path}")


def cmd_version():
    from weather_bot import __version__
    print(f"weather-slack-bot v{__version__}")


def main():
    parser = argparse.ArgumentParser(
        description="Seoul Weather Slack Bot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
commands:
  daily     Full daily weather briefing
  digest    Ultra-compact 1-block summary
  weekly    Weekly summary (past + next 7 days)
  alert     Extreme weather check
  chart     Generate temperature trend chart
  export    Export weather data as Markdown
  json      Export weather data as JSON
  history   Log today's weather & show stats
  version   Show version info
        """,
    )
    parser.add_argument(
        "command",
        choices=["daily", "digest", "weekly", "alert", "chart", "export", "json", "history", "version"],
        help="command to run",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="preview output without sending to Slack",
    )

    args = parser.parse_args()

    if args.command == "daily":
        cmd_daily(dry_run=args.dry_run)
    elif args.command == "digest":
        cmd_digest(dry_run=args.dry_run)
    elif args.command == "weekly":
        cmd_weekly()
    elif args.command == "alert":
        cmd_alert()
    elif args.command == "chart":
        cmd_chart()
    elif args.command == "export":
        cmd_export()
    elif args.command == "json":
        cmd_json()
    elif args.command == "history":
        cmd_history()
    elif args.command == "version":
        cmd_version()


if __name__ == "__main__":
    main()
