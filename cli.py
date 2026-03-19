#!/usr/bin/env python3
"""Seoul Weather Slack Bot — 통합 CLI

Usage:
    python cli.py daily      # 일일 날씨 브리핑 전송
    python cli.py weekly     # 주간 요약 전송
    python cli.py alert      # 긴급 날씨 체크 (극단적 조건 시에만 전송)
    python cli.py chart      # 기온 차트 이미지 생성
    python cli.py version    # 버전 정보 출력
"""
import argparse


def cmd_daily():
    from weather_bot import main
    main()


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
        epilog="""
commands:
  daily     Send daily weather briefing to Slack
  weekly    Send weekly summary to Slack
  alert     Check for extreme weather (sends only when needed)
  chart     Generate temperature trend chart image
  version   Show version info
        """,
    )
    parser.add_argument(
        "command",
        choices=["daily", "weekly", "alert", "chart", "version"],
        help="command to run",
    )

    args = parser.parse_args()

    commands = {
        "daily": cmd_daily,
        "weekly": cmd_weekly,
        "alert": cmd_alert,
        "chart": cmd_chart,
        "version": cmd_version,
    }

    commands[args.command]()


if __name__ == "__main__":
    main()
