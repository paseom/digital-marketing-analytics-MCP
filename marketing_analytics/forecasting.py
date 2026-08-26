from datetime import date, timedelta
from typing import List
from marketing_analytics.models import DailyTrend, ForecastPoint, ForecastResult


def _linear_regression(y_values: List[float]) -> tuple[float, float]:
    """Least-squares fit sederhana: y = a + b*x, x = index hari (0, 1, 2, ...).
    Return (intercept, slope)."""
    n = len(y_values)
    if n < 2:
        # Data terlalu sedikit buat nentuin trend — anggap flat (slope 0)
        return (y_values[0] if y_values else 0.0, 0.0)

    x_values = list(range(n))
    x_mean = sum(x_values) / n
    y_mean = sum(y_values) / n

    numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, y_values))
    denominator = sum((x - x_mean) ** 2 for x in x_values)

    slope = numerator / denominator if denominator else 0.0
    intercept = y_mean - slope * x_mean
    return (intercept, slope)


def forecast_from_daily_trends(
    history: List[DailyTrend],
    days_ahead: int,
    platform: str,
    campaign_id: str = None,
) -> ForecastResult:
    """Proyeksi spend/impressions/clicks ke depan dari data harian historis,
    pakai regresi linear terpisah untuk tiap metrik."""
    if not history:
        return ForecastResult(
            platform=platform,
            campaign_id=campaign_id,
            historical_days_used=0,
            forecast=[],
        )

    # Urutkan berdasarkan tanggal, pastikan histori-nya kronologis
    sorted_history = sorted(history, key=lambda d: d.date)

    spend_series = [d.spend for d in sorted_history]
    impressions_series = [float(d.impressions) for d in sorted_history]
    clicks_series = [float(d.clicks) for d in sorted_history]

    spend_a, spend_b = _linear_regression(spend_series)
    impr_a, impr_b = _linear_regression(impressions_series)
    click_a, click_b = _linear_regression(clicks_series)

    last_date = date.fromisoformat(sorted_history[-1].date)
    n = len(sorted_history)

    forecast_points = []
    for i in range(1, days_ahead + 1):
        x = n + i - 1  # lanjutan index dari data historis
        predicted_date = last_date + timedelta(days=i)
        forecast_points.append(
            ForecastPoint(
                date=predicted_date.isoformat(),
                spend=round(max(0.0, spend_a + spend_b * x), 2),
                impressions=max(0, round(impr_a + impr_b * x)),
                clicks=max(0, round(click_a + click_b * x)),
            )
        )

    return ForecastResult(
        platform=platform,
        campaign_id=campaign_id,
        historical_days_used=n,
        forecast=forecast_points,
    )