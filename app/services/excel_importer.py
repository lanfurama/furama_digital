import os
import pandas as pd
from app.models import DailyRate
from django.db import transaction
from django.utils import timezone
from datetime import timedelta

# === Tên cột khách sạn mapping ===
HOTEL_COLS = {
    "Furama Resort Danang": "furama_resort",
    "Hyatt Regency Danang Resort and Spa": "hyatt_regency",
    "Pullman Danang Beach Resort": "pullman_beach",
    "Sheraton Grand Danang Resort & Convention Center": "sheraton_grand",
    "Danang Marriott Resort & Spa": "danang_marriott",
    "Fusion Resort and Villas Da Nang": "fusion_resort",
    "Shilla Monogram Quangnam Danang": "shilla_monogram",
    "KOI Resort & Residence Da Nang": "koi_resort",
    "Danang Marriott Resort & Spa, Non Nuoc Beach Villas": "marriott_non_nuoc",
    "Premier Village Danang Resort Managed By Accor": "premier_village",
    "Furama Villas Danang": "furama_villas"
}

def clean_and_transform(df):
    df.columns = df.columns.str.strip().str.replace('\n', ' ').str.replace('  ', ' ', regex=False)

    rename_map = {
        df.columns[0]: "report_day",
        df.columns[1]: "excel_date",
        df.columns[2]: "my_otb",
        df.columns[3]: "market_demand"
    }
    df = df.rename(columns=rename_map)

    # Convert ngày từ Excel serial -> datetime
    if pd.api.types.is_numeric_dtype(df["excel_date"]):
        df["reported_date"] = pd.to_datetime(df["excel_date"], origin='1899-12-30', unit='d')
    else:
        df["reported_date"] = pd.to_datetime(df["excel_date"], errors="coerce")

    # Xử lý phần trăm
    df["my_otb"] = (df["my_otb"].astype(float) * 100).round(0)
    df["market_demand"] = (df["market_demand"].astype(float) * 100).round(0)

    for col in HOTEL_COLS:
        df[col] = df[col].astype(str).str.replace(",", "").str.strip()
        df[col] = df[col].replace({"No flex": 0, "Sold out": -1})
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.drop(columns=["report_day", "excel_date"], errors="ignore")
    df = df.dropna(subset=["reported_date"])

    return df

def insert_to_db(df):
    if df.empty:
        return "⚠️ File Excel không có dữ liệu hợp lệ."

    inserted = 0
    today = timezone.now()
    seven_days_ago = timezone.now() - timedelta(days=7)
    fouteen_days_ago = timezone.now() - timedelta(days=14)

    with transaction.atomic():
        for _, row in df.iterrows():
            reported_date = row["reported_date"].date()

            if DailyRate.objects.filter(reported_date=reported_date, updated_date=today).exists():
                continue;

            record = {
                "reported_date": reported_date,
                "my_otb": row["my_otb"],
                "market_demand": row["market_demand"],
                # "updated_date": today,
                # "updated_date": seven_days_ago
                "updated_date": fouteen_days_ago,  # Giả sử cập nhật lần này là 14 ngày trước
            }

            for excel_col, model_field in HOTEL_COLS.items():
                record[model_field] = row.get(excel_col)

            DailyRate.objects.create(**record)
            inserted += 1

    return inserted, None  # Không lỗi

# def import_excel_file(file_obj):
#     try:
#         df = pd.read_excel(file_obj, sheet_name="Rates", engine="openpyxl", skiprows=4, header=0)
#         df = df.drop(columns=["Unnamed: 0"], errors="ignore")

#         df_clean = clean_and_transform(df)
#         print(df_clean)
#         insert_to_db(df_clean)

#     except Exception as e:
#         print(f"❌ Lỗi khi xử lý file: {e}")
#         raise

def import_excel_file(file_obj):
    df = pd.read_excel(file_obj, sheet_name="Rates", engine="openpyxl", skiprows=4, header=0)
    df = df.drop(columns=["Unnamed: 0"], errors="ignore")
    df_clean = clean_and_transform(df)
    return insert_to_db(df_clean)  # Trả về inserted, skipped, error

