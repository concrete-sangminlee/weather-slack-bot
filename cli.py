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
    from weather_bot import now_local
    now = now_local().strftime("%Y-%m-%d %H:%M")

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


def cmd_analytics():
    """히스토리 종합 분석 리포트"""
    from history import check_forecast_accuracy, get_stats, get_trends, load_history

    history = load_history()
    if not history:
        print("히스토리가 없습니다. `weather-bot history`로 먼저 데이터를 기록하세요.")
        return

    days = len(history)
    stats = get_stats(days)
    trends = get_trends(days)
    accuracy = check_forecast_accuracy()

    print(f"""📊 날씨 분석 리포트 ({days}일간)
{'=' * 40}

🌡️ 기온 통계
   평균: {stats.get('avg_temp', 'N/A')}°C
   최고: {stats.get('highest', 'N/A')}°C / 최저: {stats.get('lowest', 'N/A')}°C
   비 온 날: {stats.get('rainy_days', 0)}일
   평균 생활지수: {stats.get('avg_score', 'N/A')}/100""")

    if trends:
        print(f"""
📈 트렌드
   기온 추세: {trends['trend']} ({trends['trend_diff']:+.1f}°C)
   최고의 날: {trends['best_day']}
   최악의 날: {trends['worst_day']}
   가장 더운 날: {trends['hottest']}
   가장 추운 날: {trends['coldest']}""")

    if accuracy:
        print(f"""
🎯 예보 정확도 (오늘)
   최고기온: 예보 {accuracy['forecast_max']}°C → 실제 {accuracy['actual_max']}°C (오차 {accuracy['max_error']}°C)
   최저기온: 예보 {accuracy['forecast_min']}°C → 실제 {accuracy['actual_min']}°C (오차 {accuracy['min_error']}°C)
   평균 오차: {accuracy['avg_error']}°C — 등급 {accuracy['grade']}""")

    # 히스토리 테이블
    print("\n📅 최근 기록 (최대 7일)")
    print(f"{'날짜':12} {'날씨':10} {'기온':>6} {'최고':>6} {'최저':>6} {'등급':>4}")
    print("-" * 50)
    for r in history[-7:]:
        print(f"{r['date']:12} {r['weather']:10} {r['temp']:>5.1f}° {r['temp_max']:>5.1f}° {r['temp_min']:>5.1f}° {r['grade']:>4}")


def cmd_compare():
    """히스토리에서 두 날짜 날씨 비교"""
    from history import load_history

    history = load_history()
    if len(history) < 2:
        print("비교하려면 최소 2일 이상의 히스토리가 필요합니다.")
        print(f"현재 {len(history)}일 기록됨. `weather-bot history`로 오늘 데이터를 먼저 저장하세요.")
        return

    latest = history[-1]
    prev = history[-2]

    temp_diff = latest["temp"] - prev["temp"]
    score_diff = latest["lifestyle_score"] - prev["lifestyle_score"]

    sign = "+" if temp_diff > 0 else ""
    s_sign = "+" if score_diff > 0 else ""

    print(f"""📊 날씨 비교: {prev['date']} vs {latest['date']}

| 항목 | {prev['date']} | {latest['date']} | 변화 |
|------|{'-' * len(prev['date']) + '--'}|{'-' * len(latest['date']) + '--'}|------|
| 날씨 | {prev['weather']} | {latest['weather']} | |
| 기온 | {prev['temp']}°C | {latest['temp']}°C | {sign}{temp_diff:.1f}°C |
| 최고 | {prev['temp_max']}°C | {latest['temp_max']}°C | {'+' if latest['temp_max'] > prev['temp_max'] else ''}{latest['temp_max'] - prev['temp_max']:.1f}°C |
| 최저 | {prev['temp_min']}°C | {latest['temp_min']}°C | {'+' if latest['temp_min'] > prev['temp_min'] else ''}{latest['temp_min'] - prev['temp_min']:.1f}°C |
| 습도 | {prev['humidity']}% | {latest['humidity']}% | |
| 등급 | {prev['grade']} ({prev['lifestyle_score']}) | {latest['grade']} ({latest['lifestyle_score']}) | {s_sign}{score_diff} |
""")


def cmd_stats():
    """프로젝트 + 날씨 히스토리 통계"""
    from pathlib import Path

    from weather_bot import __version__

    project = Path(__file__).parent

    # 코드 통계
    total_lines = 0
    py_files = 0
    for f in project.glob("*.py"):
        py_files += 1
        total_lines += len(f.read_text().splitlines())

    test_lines = 0
    for f in project.glob("tests/*.py"):
        test_lines += len(f.read_text().splitlines())

    # 히스토리 통계
    history_info = ""
    try:
        from history import get_stats, load_history
        h = load_history()
        if h:
            s = get_stats(len(h))
            history_info = (
                f"\n📊 Weather History ({len(h)} days recorded)\n"
                f"   Avg temp: {s['avg_temp']}°C | High: {s['highest']}°C | Low: {s['lowest']}°C\n"
                f"   Rainy days: {s['rainy_days']} | Avg score: {s['avg_score']}/100"
            )
    except Exception:
        pass

    print(f"""weather-slack-bot v{__version__}

📦 Code Stats
   Python files: {py_files} ({total_lines:,} lines)
   Test lines: {test_lines:,}
   Workflows: {len(list(project.glob('.github/workflows/*.yml')))}
   Locales: {len(list(project.glob('locales/*.yml')))}
{history_info}

🔗 https://github.com/concrete-sangminlee/weather-slack-bot""")


def cmd_setup():
    """대화형 초기 설정 마법사"""
    from pathlib import Path

    print("🧙 Weather Slack Bot 설정 마법사")
    print("=" * 40)

    root = Path(__file__).parent

    # 1. .env 파일 확인/생성
    env_path = root / ".env"
    if env_path.exists():
        print("✅ .env 파일 이미 존재")
    else:
        print("\n📌 Slack 연동 방식 선택:")
        print("  1) Bot Token (추천 — 전체 기능)")
        print("  2) Webhook (간편 — 기본 기능)")
        choice = input("선택 (1/2): ").strip()

        if choice == "2":
            url = input("Webhook URL: ").strip()
            env_path.write_text(f"SLACK_WEBHOOK_URL={url}\n")
        else:
            token = input("Bot Token (xoxb-...): ").strip()
            channel = input("채널명 (예: general): ").strip() or "general"
            env_path.write_text(f"SLACK_BOT_TOKEN={token}\nSLACK_CHANNEL={channel}\n")
        print("✅ .env 저장 완료")

    # 2. config.yml 도시 설정
    print(f"\n📍 현재 도시: {root / 'config.yml'}")
    change = input("도시를 변경하시겠습니까? (y/N): ").strip().lower()
    if change == "y":
        import yaml
        config_path = root / "config.yml"
        config = yaml.safe_load(config_path.read_text(encoding="utf-8"))

        name = input("도시 이름: ").strip()
        lat = input("위도 (예: 37.5665): ").strip()
        lon = input("경도 (예: 126.9780): ").strip()

        if name and lat and lon:
            config["city"]["name"] = name
            config["city"]["latitude"] = float(lat)
            config["city"]["longitude"] = float(lon)
            config_path.write_text(
                yaml.dump(config, allow_unicode=True, default_flow_style=False),
                encoding="utf-8",
            )
            print(f"✅ 도시 변경: {name} ({lat}, {lon})")

    # 3. 테스트 실행
    print("\n🧪 연결 테스트 중...")
    try:
        from weather_bot import fetch_weather
        data = fetch_weather()
        temp = data["current"]["temperature_2m"]
        print(f"✅ 날씨 API 연결 성공! 현재 기온: {temp}°C")
    except Exception as e:
        print(f"❌ API 오류: {e}")
        return

    print("\n🎉 설정 완료! 다음 명령어로 테스트하세요:")
    print("   weather-bot daily --dry-run")
    print("   weather-bot daily")


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
  analytics Full history analysis report
  compare   Compare last 2 days from history
  stats     Project + weather history statistics
  setup     Interactive setup wizard
  version   Show version info
        """,
    )
    parser.add_argument(
        "command",
        choices=["daily", "digest", "weekly", "alert", "chart", "export", "json", "history", "analytics", "compare", "stats", "setup", "version"],
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
    elif args.command == "analytics":
        cmd_analytics()
    elif args.command == "compare":
        cmd_compare()
    elif args.command == "stats":
        cmd_stats()
    elif args.command == "setup":
        cmd_setup()
    elif args.command == "version":
        cmd_version()


if __name__ == "__main__":
    main()
