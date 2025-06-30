from django.shortcuts import render
from django.http import HttpResponse
from django.template.loader import render_to_string
from app.models import DailyRate
from datetime import timedelta, date
from collections import defaultdict
from decimal import Decimal, InvalidOperation
import math
from django.shortcuts import redirect
from app.services.excel_importer import import_excel_file
from django.contrib import messages

# ========================
# Utilities
# ========================

def is_nan(value):
    try:
        if isinstance(value, float):
            return math.isnan(value)
        elif isinstance(value, Decimal):
            return value.is_nan()
    except (TypeError, InvalidOperation):
        return False
    return False

def format_currency(value, is_percent=False):
    if is_nan(value):
        return "--"
    if value == -1:
        return "Flex out"
    if value == 0:
        return "Sold out"
    if is_percent:
        return f"{round(value):,d}%"
    return f"{value:,.0f}₫"


def get_compare_display(value, is_percent=False):
    if value == -1:
        return "Flex out"
    if value == 0:
        return "Sold out"
    return format_currency(value, is_percent)


def get_change_display(latest, compare, is_percent=False):
    if compare == -1:
        return "↗ từ Flex out"
    if compare == 0:
        return "↗ từ Sold out"
    diff = latest - compare
    return f"{diff:+,.1f}" + ("%" if is_percent else "₫")


def get_trend_data(latest, compare):
    if isinstance(compare, (int, float)) and compare > 0:
        try:
            percent = ((latest - compare) / compare) * 100
            percent = max(min(percent, 100), -100)
            return {
                "percent": f"{int(percent):+d}%",
                "trend": "up" if percent > 0 else "down"
            }
        except ZeroDivisionError:
            return None
    return None


def create_cell(latest_value, compare_value, compare_date=None, is_percent=False):
    if latest_value is None or is_nan(latest_value):
        return {"display": "--"}
    if latest_value == 0:
        return {"display": "Flex out"}
    if latest_value == -1:
        return {"display": "Sold out"}

    # Format giá trị hiện tại
    display = format_currency(latest_value, is_percent)

    if compare_value not in [None, 0, -1] and not is_nan(compare_value):
        try:
            percent = ((latest_value - compare_value) / compare_value) * 100
            percent = max(min(percent, 100), -100)
            if percent:
                data = {
                    "display": display,
                    "percent": f"{int(percent):+d}%",
                    "trend": "up" if percent > 0 else "down",
                    "latest": display,
                    "compare": format_currency(compare_value, is_percent),
                    "change": f"{(latest_value - compare_value):+,.1f}" + ("%" if is_percent else "₫"),
                    "compare_date": compare_date.strftime("%d/%m/%Y") if compare_date else None,
                    "tooltip": True,
                }
                return data
            else:
                return {
                    "display": display,
                    "latest": display,
                }
        except Exception as e:
            return {"display": display}
    else:
        return {
            "display": display,
            "latest": display,
        }

# ========================
# Constants
# ========================

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

# ========================
# Data Processing
# ========================

def find_comparable_entry(latest, entries, comparison_days):
    latest_date = latest.updated_date.date()
    target_date = latest_date - timedelta(days=comparison_days)

    # Loại trừ bản mới nhất
    candidates = [r for r in entries if r != latest and r.updated_date.date() < latest_date]

    if not candidates:
        return None

    # Ưu tiên bản có ngày gần nhất với target_date (trong quá khứ)
    candidates.sort(key=lambda r: abs((r.updated_date.date() - target_date).days))

    return candidates[0]


def group_rates_by_reported_date(rates):
    grouped = defaultdict(list)
    for rate in rates:
        grouped[rate.reported_date].append(rate)
    return grouped

def process_rate_row(report_date, entries, comparison_days):
    entries.sort(key=lambda x: x.updated_date, reverse=True)
    latest = entries[0]
    date_status = "today" if report_date == date.today() else "future" if report_date > date.today() else "past"

    compare = find_comparable_entry(latest, entries, comparison_days)

    row = {
        "reported_date": report_date.strftime("%d/%m/%Y"),
        "updated_date": latest.updated_date.strftime("%d/%m/%Y"),
        "cells": [],
        "date_status": date_status
    }

    for field, _ in COLUMNS:
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

    return row

# ========================
# View
# ========================

def dashboard(request, comparison_period=7):
    comparison_days = int(comparison_period)
    rates = DailyRate.objects.order_by('reported_date')
    grouped_rates = group_rates_by_reported_date(rates)

    rows = [
        process_rate_row(report_date, daily_entries, comparison_days)
        for report_date, daily_entries in grouped_rates.items()
    ]

    context = {
        "rows": rows,
        "columns": COLUMNS,
        "comparison_period": comparison_period
    }

    if request.headers.get("HX-Request") == "true":
        html = render_to_string("rates/partials/rates_table_rows.html", context)
        return HttpResponse(html)

    return render(request, "rates/index.html", context)

def import_excel(request):
    if request.method == "POST" and request.FILES.get("excel_file"):
        excel_file = request.FILES["excel_file"]
        try:
            inserted, error = import_excel_file(excel_file)
            if error:
                messages.warning(request, error)
            else:
                messages.success(request, f"✅ Import thành công {inserted} dòng mới.")
        except Exception as e:
            print(f"❌ Lỗi khi import file: {e}")
            messages.error(request, f"❌ Lỗi khi import file: {e}")
    else:
        messages.warning(request, "⚠️ Bạn chưa chọn file.")

    return redirect("daily_rates_dashboard")
