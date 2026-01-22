import sys
from pathlib import Path

import gspread
import pandas as pd
import plotly.express as px

 codex/update-.gitignore-for-flow-analytics-wmrhlb
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.append(str(SCRIPT_DIR))

from plotly_html_effects import write_html_with_effects


 main
try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - fallback for Python < 3.11
    import tomli as tomllib


SECRETS_PATH = Path(".streamlit/secrets.toml")
OUTPUT_DIR = Path("outputs")
REQUIRED_COLUMNS = ["投資地區", "資產類別", "代號", "名稱", "總市值(TWD)"]


def load_config() -> dict:
    if not SECRETS_PATH.exists():
        raise FileNotFoundError(
            "Missing .streamlit/secrets.toml. Please create it locally."
        )

    with SECRETS_PATH.open("rb") as handle:
        data = tomllib.load(handle)

    gsheets = data.get("gsheets", {})
    return {
        "spreadsheet_id": gsheets.get("spreadsheet_id"),
        "worksheet": gsheets.get("worksheet", "holdings"),
        "service_account_json_path": gsheets.get(
            "service_account_json_path",
            "data/private/service_account.json",
        ),
    }


def validate_config(config: dict) -> None:
    if not config.get("spreadsheet_id"):
        raise ValueError("Missing spreadsheet_id in .streamlit/secrets.toml")

    if not config.get("service_account_json_path"):
        raise ValueError("Missing service_account_json_path in .streamlit/secrets.toml")


def load_holdings(config: dict) -> pd.DataFrame:
    service_account_path = Path(config["service_account_json_path"])
    if not service_account_path.exists():
        raise FileNotFoundError(
            f"Service account JSON not found at {service_account_path}"
        )

    client = gspread.service_account(filename=str(service_account_path))
    spreadsheet = client.open_by_key(config["spreadsheet_id"])
    worksheet = spreadsheet.worksheet(config["worksheet"])
    records = worksheet.get_all_records()
    return pd.DataFrame(records)


def redact_preview(df: pd.DataFrame) -> str:
    preview = df.head(3).copy()
    for column in preview.columns:
        preview[column] = preview[column].apply(
            lambda value: "***" if pd.notna(value) else ""
        )
    return preview.to_string(index=False)


def raise_validation_error(message: str, df: pd.DataFrame) -> None:
    columns = list(df.columns)
    preview = redact_preview(df)
    raise ValueError(
        f"{message}\nColumns: {columns}\nPreview (redacted):\n{preview}"
    )


def clean_holdings(df: pd.DataFrame) -> pd.DataFrame:
    missing = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing:
        raise_validation_error(f"Missing required columns: {', '.join(missing)}", df)

    df = df.copy()
    df["總市值(TWD)"] = (
        df["總市值(TWD)"]
        .astype(str)
        .str.replace(",", "", regex=False)
        .replace("", pd.NA)
    )
    df["總市值(TWD)"] = pd.to_numeric(df["總市值(TWD)"], errors="coerce")

    if df["總市值(TWD)"].isna().all():
        raise_validation_error("Column 總市值(TWD) has no valid numeric values.", df)

    df = df[df["總市值(TWD)"] > 0]
    if df.empty:
        raise_validation_error("No rows with 總市值(TWD) > 0.", df)

    return df


def build_sunburst(df: pd.DataFrame) -> px.sunburst:
 codex/update-.gitignore-for-flow-analytics-wmrhlb
    fig_sunburst = px.sunburst(

 codex/update-.gitignore-for-flow-analytics-av70ig
    fig_sunburst = px.sunburst(

    fig = px.sunburst( main
 main
        df,
        path=["投資地區", "資產類別", "代號"],
        values="總市值(TWD)",
        hover_data={"名稱": True, "總市值(TWD)": ":,.0f"},
    )
 codex/update-.gitignore-for-flow-analytics-wmrhlb
    # 加入平滑轉場動畫
    fig_sunburst.update_layout(
        transition={
            "duration": 700,  # 動畫持續 700 毫秒
            "easing": "elastic-out",  # 更有彈性的緩出效果
        }
    )
    fig_sunburst.update_layout(

 codex/update-.gitignore-for-flow-analytics-av70ig
    # 加入平滑轉場動畫
    fig_sunburst.update_layout(
        transition={
            "duration": 1000,  # 動畫持續 1000 毫秒 (1秒)
            "easing": "cubic-in-out",  # 緩入緩出的平滑效果曲線
        }
    )
    fig_sunburst.update_layout(

    fig.update_layout(
 main
 main
        title="Flow-Analytics｜Sunburst（地區 → 資產 → 個股）",
        margin=dict(t=80, l=20, r=20, b=20),
        font=dict(size=14),
        uniformtext=dict(minsize=10, mode="hide"),
    )
 codex/update-.gitignore-for-flow-analytics-wmrhlb
    fig_sunburst.update_traces(

 codex/update-.gitignore-for-flow-analytics-av70ig
    fig_sunburst.update_traces(

    fig.update_traces(
 main
 main
        hovertemplate=(
            "<b>%{label}</b><br>"
            "名稱: %{customdata[0]}<br>"
            "總市值(TWD): %{value:,.0f}<br>"
            "<extra></extra>"
        )
    )
 codex/update-.gitignore-for-flow-analytics-wmrhlb
    return fig_sunburst


 codex/update-.gitignore-for-flow-analytics-av70ig
    return fig_sunburst

    return fig
 main

 main

def build_treemap(df: pd.DataFrame) -> px.treemap:
    fig = px.treemap(
        df,
        path=["投資地區", "代號"],
        values="總市值(TWD)",
        hover_data={"名稱": True, "總市值(TWD)": ":,.0f"},
    )
    fig.update_layout(
        title="Flow-Analytics｜Treemap（地區 → 個股）",
        margin=dict(t=80, l=20, r=20, b=20),
        font=dict(size=14),
        uniformtext=dict(minsize=10, mode="hide"),
    )
    fig.update_traces(
        hovertemplate=(
            "<b>%{label}</b><br>"
            "名稱: %{customdata[0]}<br>"
            "總市值(TWD): %{value:,.0f}<br>"
            "<extra></extra>"
        )
    )
    return fig


def main() -> int:
    try:
        config = load_config()
        validate_config(config)
        df = load_holdings(config)
        df = clean_holdings(df)

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        sunburst_path = OUTPUT_DIR / "sunburst.html"
        treemap_path = OUTPUT_DIR / "treemap.html"

 codex/update-.gitignore-for-flow-analytics-wmrhlb
        write_html_with_effects(build_sunburst(df), sunburst_path, "sunburst")
        write_html_with_effects(build_treemap(df), treemap_path, "treemap")

        build_sunburst(df).write_html(str(sunburst_path), include_plotlyjs="cdn")
        build_treemap(df).write_html(str(treemap_path), include_plotlyjs="cdn")
 main

        print("✅ 圖表已生成：outputs/sunburst.html")
        return 0
    except FileNotFoundError as error:
        print(f"Error: {error}")
    except gspread.exceptions.WorksheetNotFound as error:
        print(f"Error: Worksheet not found: {error}")
    except gspread.exceptions.SpreadsheetNotFound as error:
        print(f"Error: Spreadsheet not found or no access: {error}")
    except gspread.exceptions.APIError as error:
        print(f"Error: Google API error: {error}")
    except ValueError as error:
        print(f"Error: {error}")
    except Exception as error:
        print(f"Unexpected error: {error}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
