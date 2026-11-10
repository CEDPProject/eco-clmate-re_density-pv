# -*- coding: utf-8 -*-

"""
main_solar.py

KIM LDAPS 태양광 일평균 에너지밀도 및
월평균 잠재발전량 계산

입력
------
/data/jyy/S82_2025/KIML_monthly/2026/MM/DD/12/*.nc

사용자료
--------
ft000 ~ ft023

출력
------
output/excel/solar_daily_density_summary.xlsx
output/excel/solar_monthly_density.xlsx

"""

import os
import sys
import pandas as pd
import numpy as np

from datetime import datetime
from datetime import timedelta


# =====================================================
# PATH
# =====================================================

CODE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

sys.path.append(CODE_DIR)


# =====================================================
# IMPORT
# =====================================================

from config import (
    START_DATE,
    END_DATE,
    OUTPUT_DIR
)

from solar.pv_calc import (
    get_daily_files,
    calc_daily_pv
)


# =====================================================
# 날짜 반복
# =====================================================

def daterange(start_date, end_date):

    start = datetime.strptime(start_date, "%Y%m%d")
    end = datetime.strptime(end_date, "%Y%m%d")

    while start <= end:

        yield start

        start += timedelta(days=1)


# =====================================================
# MAIN
# =====================================================

def main():

    print("=" * 50)
    print("SOLAR MONTHLY PROCESS START")
    print("=" * 50)

    # ----------------------------------------
    # 저장용
    # ----------------------------------------

    daily_summary = []

    monthly_sum = {}

    monthly_count = {}

    # ----------------------------------------
    # 날짜 반복
    # ----------------------------------------

    for current in daterange(
            START_DATE,
            END_DATE):

        yyyy = current.year
        mm = current.month
        dd = current.day

        datestr = current.strftime("%Y-%m-%d")

        monthkey = current.strftime("%Y-%m")

        print("PROCESS :", datestr)

        files = get_daily_files(
            yyyy,
            mm,
            dd
        )

        if len(files) == 0:

            print("   NO FILE")

            continue

        print("   FILE :", len(files))

        result = calc_daily_pv(files)

        if result is None:

            continue

        lats, lons, density = result

        # ------------------------------------
        # [핵심 추가 1] 일별 데이터 이상치 필터링
        # 하루 일사량이 12 kWh/m2/day를 초과하거나 0 미만인 노이즈는 NaN 처리
        # ------------------------------------
        density = np.where((density >= 0) & (density <= 12.0), density, np.nan)

        # ------------------------------------
        # 일평균 통계
        # ------------------------------------

        mean_value = float(np.nanmean(density))
        max_value = float(np.nanmax(density))
        min_value = float(np.nanmin(density))

        daily_summary.append({

            "date": datestr,

            "mean_kWh_m2_day": round(mean_value, 4),

            "max_kWh_m2_day": round(max_value, 4),

            "min_kWh_m2_day": round(min_value, 4)

        })

        # ------------------------------------
        # 월평균 누적 (NaN 안전 처리)
        # ------------------------------------

        if monthkey not in monthly_sum:

            monthly_sum[monthkey] = np.nan_to_num(density, nan=0.0)

            monthly_count[monthkey] = np.where(np.isnan(density), 0, 1)

        else:

            monthly_sum[monthkey] += np.nan_to_num(density, nan=0.0)

            monthly_count[monthkey] += np.where(np.isnan(density), 0, 1)

    print()

    print("=" * 50)
    print("SAVE EXCEL")
    print("=" * 50)

    excel_dir = os.path.join(
        OUTPUT_DIR,
        "excel"
    )

    os.makedirs(
        excel_dir,
        exist_ok=True
    )
    # ==================================================
    # 월평균 격자(npz) 저장 폴더
    # ==================================================

    grid_dir = os.path.join(
        OUTPUT_DIR,
        "solar_grid"
    )

    os.makedirs(
        grid_dir,
        exist_ok=True
    )
    # ==================================================
    # 일별 요약 저장
    # ==================================================

    df_daily = pd.DataFrame(
        daily_summary
    )

    outfile = os.path.join(
        excel_dir,
        "solar_daily_density_summary.csv"
    )

    df_daily.to_csv(
        outfile,
        index=False,
        encoding="utf-8-sig"
    )

    print(outfile)

    # ==================================================
    # 월평균 저장
    # ==================================================

    monthly_records = []

    for monthkey in sorted(monthly_sum.keys()):

        # 유효한 데이터가 있는 횟수로 나누어 정확한 월평균 산출
        count_mask = monthly_count[monthkey]
        avg = np.where(count_mask > 0, monthly_sum[monthkey] / count_mask, np.nan)
        
        # ----------------------------------------
        # [핵심 추가 2] 월평균 데이터 최종 이상치 필터링
        # ----------------------------------------
        avg = np.where((avg >= 0) & (avg <= 12.0), avg, np.nan)

        # 월평균 격자 저장
        # ----------------------------------------

        np.savez_compressed(

            os.path.join(
                grid_dir,
                monthkey.replace("-", "_") + ".npz"
            ),

            lat=lats,

            lon=lons,

            density=avg

        )

        monthly_records.append({

            "month": monthkey,

            "mean_kWh_m2_day":
                round(
                    float(np.nanmean(avg)),
                    4
                ),

            "max_kWh_m2_day":
                round(
                    float(np.nanmax(avg)),
                    4
                ),

            "min_kWh_m2_day":
                round(
                    float(np.nanmin(avg)),
                    4
                )

        })

    df_month = pd.DataFrame(
        monthly_records
    )

    outfile = os.path.join(
        excel_dir,
        "solar_monthly_density.csv"
    )

    df_month.to_csv(
        outfile,
        index=False,
        encoding="utf-8-sig"     
    )

    print(outfile)

    print()

    print("=" * 50)
    print("COMPLETE")
    print("=" * 50)


# =====================================================
# 실행
# =====================================================

if __name__ == "__main__":

    main()