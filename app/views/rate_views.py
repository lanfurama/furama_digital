from django.shortcuts import render
from django.http import HttpResponse
from django.template.loader import render_to_string
from app.models import DailyRate
from datetime import timedelta, date
from django.http import JsonResponse
from collections import defaultdict
from decimal import Decimal, InvalidOperation
import math
from django.shortcuts import redirect
from app.services.excel_importer import import_excel_file
from django.contrib import messages
from django.utils.dateparse import parse_date
from datetime import datetime, timedelta, date
from app.services.automation.lighthouse.fetch_rates import LighthouseRateFetcher
import calendar

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
    # Định dạng số liệu để hiển thị ra frontend, tuỳ vào loại dữ liệu (giá tiền hoặc phần trăm)
    if is_nan(value):
        return "--"
    if value == -1:
        return "Flex out"
    if value == 0:
        return "Sold out"
    if is_percent:
        return f"{round(value):,d}%"
    return f"{value:,.0f}₫"


def create_cell(latest_value, compare_value, latest_date=None, compare_date=None, is_percent=False):
    # Tạo dữ liệu cho từng ô trong bảng, bao gồm logic tính phần trăm chênh lệch và tooltip
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
                    "percent": f"{percent:+.1f}%",
                    "trend": "up" if percent > 0 else "down",
                    "latest": display,
                    "latest_date": latest_date,
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

def find_comparable_entry(latest, entries, start_dt=None, end_dt=None):
    # Danh sách ngày hợp lệ, đã sort giảm dần theo updated_date
    sorted_entries = sorted(
        [e for e in entries if e != latest],
        key=lambda r: r.updated_date,
        reverse=True
    )

    # Trường hợp có start_dt và end_dt từ request
    if start_dt and end_dt:
        candidates = [
            e for e in sorted_entries
            if start_dt <= e.updated_date <= end_dt
        ]
        return candidates[0] if candidates else None

    # Nếu không có start và end, tự động chọn 2 bản gần nhất
    for e in sorted_entries:
        if e.updated_date < latest.updated_date:
            return e

    return None


def group_rates_by_reported_date(rates):
    grouped = defaultdict(list)
    for rate in rates:
        grouped[rate.reported_date].append(rate)
    return grouped

def process_rate_row(report_date, entries, start_dt=None, end_dt=None):
    entries.sort(key=lambda x: x.updated_date, reverse=True)
    latest = entries[0]
    date_status = "today" if report_date == date.today() else "future" if report_date > date.today() else "past"

    compare = find_comparable_entry(latest, entries, start_dt, end_dt)

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
            latest.updated_date if latest else None,
            compare.updated_date if compare else None,
            is_percent
        )
        row["cells"].append(cell)

    return row


def get_date_range(request):
    start_str = request.GET.get("start")
    end_str = request.GET.get("end")
    month_str = request.GET.get("month")

    # Nếu có tham số start & end trong URL
    if start_str and end_str:
        return parse_date(start_str), parse_date(end_str), month_str

    # Lấy tất cả ngày có trong DB
    updated_dates = DailyRate.objects.order_by("updated_date").values_list("updated_date", flat=True).distinct()
    if not updated_dates:
        today = date.today()
        return today - timedelta(days=7), today

    # Lấy ngày mới nhất
    end = updated_dates.last().date()

    # Tìm ngày gần nhất trước ngày mới nhất
    dates_before = [d.date() for d in updated_dates if d.date() < end]
    start = max(dates_before) if dates_before else end  # fallback nếu chỉ có 1 ngày

    return start, end, month_str


def build_comparison_rows(grouped_rates, start_dt, end_dt, month_str=None):
    rows = []
    today = date.today()

    for report_date, entries in grouped_rates.items():
        # if month_str:
        #     # Lọc theo tháng nếu có tháng
        #     if report_date.strftime("%Y-%m") != month_str:
        #         continue  # Nếu reported_date không phải tháng được chọn, bỏ qua

        latest = find_latest_before(entries, end_dt)
        compare = find_latest_before(entries, start_dt)

        if not latest:
            continue

        row = {
            "reported_date": report_date.strftime("%d/%m/%Y"),
            "updated_date": latest.updated_date.strftime("%d/%m/%Y"),
            "date_status": (
                "today" if report_date == today
                else "future" if report_date > today
                else "past"
            ),
            "cells": [],
        }

        for field, _ in COLUMNS:
            latest_value = getattr(latest, field, None)
            compare_value = getattr(compare, field, 0) if compare else 0
            is_percent = field in ["my_otb", "market_demand"]

            cell = create_cell(
                latest_value,
                compare_value,
                latest.updated_date.strftime("%d/%m/%Y"),
                compare.updated_date if compare else None,
                is_percent
            )
            row["cells"].append(cell)

        rows.append(row)

    return rows


def find_latest_before(entries, target_dt):
    candidates = [r for r in entries if r.updated_date <= target_dt]
    return max(candidates, key=lambda r: r.updated_date) if candidates else None


# ========================
# View
# ========================
def index(request):
    # 1. Xử lý ngày bắt đầu và kết thúc
    start_date, end_date, month_str = get_date_range(request)

    if not month_str:
        month_str = datetime.now().strftime("%Y-%m")

    # 2. Tách tháng và năm từ month_str (ví dụ: '2025-07')
    year, month = map(int, month_str.split('-'))
    print(f"Filtering rates for month: {month_str} (Year: {year}, Month: {month})")

    # 2. Ép thành datetime để filter chính xác
    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.max.time())

    # 3. Truy vấn dữ liệu
    # rates = DailyRate.objects.filter(updated_date__lte=end_dt, reported_date__year=year, reported_date__month=month).order_by("reported_date")
    rates = DailyRate.objects.filter(updated_date__lte=end_dt).order_by("reported_date")
    print(end_dt)
    valid_dates = sorted(set(rate.updated_date.strftime('%Y-%m-%d') for rate in rates))
    grouped_rates = group_rates_by_reported_date(rates)

     # 4. Xử lý bảng
    rows = build_comparison_rows(grouped_rates, start_dt, end_dt, month_str)

    # 5. Tạo context
    context = {
        "total_rates": rates.count(),
        "total_rows": len(rows),
        "rows": rows,
        "columns": COLUMNS,
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d"),
        "valid_dates": valid_dates, 
    }

    if request.headers.get("HX-Request") == "true":
        html = render_to_string("rates/partials/rates_table_rows.html", context)
        return HttpResponse(html)

    return render(request, "rates/index.html", context)
    # return JsonResponse(context)
