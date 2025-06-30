from django.shortcuts import render
from django.http import HttpResponse
from django.utils import timezone
from django.template.loader import render_to_string
from .models import DailyRate
from datetime import timedelta
from collections import defaultdict
from decimal import Decimal, InvalidOperation
import math
from datetime import date

# Kiểm tra giá trị NaN
def is_nan(value):
    try:
        if isinstance(value, float):
            return math.isnan(value)
        elif isinstance(value, Decimal):
            return value.is_nan()
    except (TypeError, InvalidOperation):
        return False
    return False

# Cấu hình các cột hiển thị
COLUMNS = [
    ("my_otb", "My OTB"),
    ("market_demand", "Market Demand"),
    ("furama_resort", "Furama Resort"),
    ("hyatt_regency", "Hyatt Regency"),
    ("pullman_beach", "Pullman Beach"),
    ("sheraton_grand", "Sheraton Grand"),
    ("danang_marriott", "Danang Marriott"),
    ("fusion_resort", "Fusion Resort"),
    ("shilla_monogram", "Shilla Monogram"),
    ("koi_resort", "KOI Resort"),
    ("marriott_non_nuoc", "Marriott Non Nuoc"),
    ("premier_village", "Premier Village"),
    ("furama_villas", "Furama Villas"),
]

# Tạo dữ liệu cho mỗi ô (cell)
def create_cell(latest_value, compare_value, compare_date=None, is_percent=False):
    if latest_value is None or is_nan(latest_value):
        return {"display": "--"}
    if latest_value == 0:
        return {"display": "Flex out"}
    if latest_value == -1:
        return {"display": "Sold out"}

    def fmt(value):
        if is_nan(value):
            return "--"
        if is_percent:
            return f"{round(value * 100):,d}%"
        return f"{value:,.0f}₫"

    if compare_value not in [None, 0] and not is_nan(compare_value):
        try:
            percent = ((latest_value - compare_value) / compare_value) * 100
            return {
                "display": fmt(latest_value),
                "percent": f"{percent:+.1f}%",
                "trend": "up" if percent > 0 else "down",
                "latest": fmt(latest_value),
                "compare": fmt(compare_value),
                "change": f"{(latest_value - compare_value):+,.1f}" + ("%" if is_percent else "₫"),
                "compare_date": compare_date.strftime("%d/%m/%Y") if compare_date else None,
                "tooltip": True,
            }
        except Exception as e:
            print(f"Error calculating percent: {e}")
            return {"display": f"{latest_value:.2f}"}
    else:
        return {
            "display": fmt(latest_value),
            "latest": fmt(latest_value),
        }

# View hiển thị dashboard
def dashboard(request, comparison_period=7):
    comparison_days = int(comparison_period)

    # Lấy toàn bộ dữ liệu từ DB, sắp theo reported_date
    rates = DailyRate.objects.order_by('reported_date')

    # Nhóm theo reported_date
    grouped_rates = defaultdict(list)
    for rate in rates:
        grouped_rates[rate.reported_date].append(rate)

    rows = []

    for report_date, daily_entries in grouped_rates.items():
        # Sắp theo updated_date giảm dần
        daily_entries.sort(key=lambda x: x.updated_date, reverse=True)
        latest = daily_entries[0]
        date_status = "today" if report_date == date.today() else "future" if report_date > date.today() else "past"

        # Tìm bản ghi có updated_date cách latest đúng comparison_days
        compare = next(
            (r for r in daily_entries[1:]
             if (latest.updated_date.date() - r.updated_date.date()).days == comparison_days),
            None
        )

        row = {
            "reported_date": report_date.strftime("%d/%m/%Y"),
            "updated_date": latest.updated_date.strftime("%d/%m/%Y"),
            "cells": [],
            "date_status": date_status
        }

        for field, _label in COLUMNS:
            latest_value = getattr(latest, field, None)
            compare_value = getattr(compare, field, 0) if compare else 0
            is_percent = field in ["my_otb", "market_demand"]

            cell = create_cell(
                latest_value,
                compare_value,
                compare.updated_date if compare else None,
                is_percent
            )
            row["cells"].append(cell)

        rows.append(row)

    context = {
        "rows": rows,
        "columns": COLUMNS,
        "comparison_period": comparison_period
    }

    # Trả về partial nếu là HTMX
    if request.headers.get("HX-Request") == "true":
        html = render_to_string("dashboard/partials/rates_table_rows.html", context)
        return HttpResponse(html)

    # Trả về trang đầy đủ
    return render(request, "dashboard/index.html", context)
