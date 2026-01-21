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
DEFAULT_SPREADSHEET_ID = "1Ks6m4-Nkn4BK-83pBH879eb5f6v_L3mxc6zuUMeDq9A"
REQUIRED_COLUMNS = ["投資地區", "代號", "名稱", "總市值 (TWD)"]


def load_config() -> dict:
    if not SECRETS_PATH.exists():
        raise FileNotFoundError(
            "Missing .streamlit/secrets.toml. Please create it locally."
        )

    with SECRETS_PATH.open("rb") as handle:
        data = tomllib.load(handle)

    gsheets = data.get("gsheets", {})
    return {
        "spreadsheet_id": gsheets.get("spreadsheet_id") or DEFAULT_SPREADSHEET_ID,
        "worksheet": gsheets.get("worksheet", "holdings"),
        "service_account_json_path": gsheets.get(
            "service_account_json_path",
            "data/private/service_account.json",
        ),
    }


def validate_config(config: dict) -> None:
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


def redacted_preview(df: pd.DataFrame) -> str:
    preview = df.head(3).copy()
    for column in preview.columns:
        preview[column] = preview[column].apply(
            lambda value: "***" if pd.notna(value) else ""
        )
    return preview.to_string(index=False)


def raise_validation_error(message: str, df: pd.DataFrame) -> None:
    columns = list(df.columns)
    preview = redacted_preview(df)
    raise ValueError(
        f"{message}\nColumns: {columns}\nPreview (redacted):\n{preview}"
    )


def validate_columns_and_values(df: pd.DataFrame) -> pd.DataFrame:
    missing = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing:
        raise_validation_error(f"Missing required columns: {', '.join(missing)}", df)

    numeric = pd.to_numeric(df["總市值 (TWD)"], errors="coerce")
    invalid_mask = df["總市值 (TWD)"].notna() & numeric.isna()
    if invalid_mask.any():
        raise_validation_error("Invalid numeric values in 總市值 (TWD).", df)

    df = df.copy()
    df["總市值 (TWD)"] = numeric
    df = df.dropna(subset=["總市值 (TWD)"])
    if df.empty:
        raise_validation_error("No valid values found in 總市值 (TWD).", df)
    return df


def build_display_name(df: pd.DataFrame) -> pd.Series:
    symbols = df["代號"].astype(str).str.strip()
    names = df["名稱"].astype(str).str.strip()
    display = symbols
    has_name = names.ne("") & names.ne("nan")
    display = display.where(~has_name, display + " " + names)
    return display


def build_sunburst(df: pd.DataFrame) -> px.sunburst:
    df = df.copy()
    df["顯示名稱"] = build_display_name(df)

    fig = px.sunburst(
        df,
        path=["投資地區", "顯示名稱"],
        values="總市值 (TWD)",
    )
    fig.update_layout(
        title="Flow-Analytics｜資產配置（地區 → 個股）",
        margin=dict(t=80, l=20, r=20, b=20),
        font=dict(size=14),
        uniformtext=dict(minsize=10, mode="hide"),
    )
    fig.update_traces(
        hovertemplate=(
            "<b>%{label}</b><br>"
            "總市值 (TWD): %{value:,.0f}<br>"
            "佔比(全體): %{percentRoot:.1%}<br>"
            "佔比(母節點): %{percentParent:.1%}"
            "<extra></extra>"
        )
    )
    return fig


def build_figure_from_gsheets() -> px.sunburst:
    config = load_config()
    validate_config(config)
    df = load_holdings(config)
    df = validate_columns_and_values(df)
    return build_sunburst(df)


def main() -> int:
    try:
        fig = build_figure_from_gsheets()
        print("Sunburst figure created successfully.")
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
