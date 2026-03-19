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

    blocks, color = build_blocks(data, air_data)
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
  version   Show version info
        """,
    )
    parser.add_argument(
        "command",
        choices=["daily", "digest", "weekly", "alert", "chart", "version"],
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
    elif args.command == "version":
        cmd_version()


if __name__ == "__main__":
    main()
