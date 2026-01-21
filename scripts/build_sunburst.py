import sys
from pathlib import Path

import gspread
import pandas as pd
import plotly.express as px

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - fallback for Python < 3.11
    import tomli as tomllib


SECRETS_PATH = Path(".streamlit/secrets.toml")
OUTPUT_PATH = Path("outputs/sunburst_holdings.html")
REQUIRED_COLUMNS = ["投資地區", "幣別", "代號", "總市值(TWD)"]


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


def validate_columns(df: pd.DataFrame) -> None:
    missing = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing:
        missing_text = ", ".join(missing)
        raise ValueError(f"Missing required columns: {missing_text}")

    if df["總市值(TWD)"].isna().all():
        raise ValueError("Column 總市值(TWD) is empty.")


def build_sunburst(df: pd.DataFrame) -> px.sunburst:
    chart_df = df[REQUIRED_COLUMNS].copy()
    chart_df["總市值(TWD)"] = pd.to_numeric(
        chart_df["總市值(TWD)"], errors="coerce"
    )
    chart_df = chart_df.dropna(subset=["總市值(TWD)"])

    if chart_df.empty:
        raise ValueError("No valid values found in 總市值(TWD).")

    fig = px.sunburst(
        chart_df,
        path=["投資地區", "幣別", "代號"],
        values="總市值(TWD)",
        hover_data={"名稱": True} if "名稱" in chart_df.columns else None,
    )
    fig.update_layout(
        title="Flow-Analytics｜資產配置（地區 → 幣別 → 個股）",
        margin=dict(t=80, l=20, r=20, b=20),
        font=dict(size=14),
    )
    fig.update_traces(hovertemplate=None)
    return fig


def save_output(fig: px.sunburst) -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(str(OUTPUT_PATH), include_plotlyjs="cdn")


def main() -> int:
    try:
        config = load_config()
        validate_config(config)
        df = load_holdings(config)
        validate_columns(df)
        fig = build_sunburst(df)
        save_output(fig)
        print(f"Sunburst chart saved to {OUTPUT_PATH}")
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
