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
OUTPUT_DIR = Path("outputs")
REQUIRED_COLUMNS = ["投資地區", "資產類別", "代號", "名稱", "總市值(TWD)"]


def load_config() -> dict:
    if not SECRETS_PATH.exists():
        raise FileNotFoundError("Missing .streamlit/secrets.toml. Please create it locally.")

    with SECRETS_PATH.open("rb") as handle:
        data = tomllib.load(handle)

    gsheets = data.get("gsheets", {})
    spreadsheet_id = gsheets.get("spreadsheet_id")
    worksheet = gsheets.get("worksheet", "holdings")
    service_account_json_path = gsheets.get("service_account_json_path", "data/private/service_account.json")

    return {
        "spreadsheet_id": spreadsheet_id,
        "worksheet": worksheet,
        "service_account_json_path": service_account_json_path,
    }


def validate_config(config: dict) -> None:
    if not config.get("spreadsheet_id"):
        raise ValueError("Missing spreadsheet_id in .streamlit/secrets.toml")

    if not config.get("service_account_json_path"):
        raise ValueError("Missing service_account_json_path in .streamlit/secrets.toml")


def load_holdings(config: dict) -> pd.DataFrame:
    service_account_path = Path(config["service_account_json_path"])
    if not service_account_path.exists():
        raise FileNotFoundError(f"Service account JSON not found at {service_account_path}")

    client = gspread.service_account(filename=str(service_account_path))
    spreadsheet = client.open_by_key(config["spreadsheet_id"])
    worksheet = spreadsheet.worksheet(config["worksheet"])
    records = worksheet.get_all_records()
    return pd.DataFrame(records)


def clean_holdings(df: pd.DataFrame) -> pd.DataFrame:
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")

    df = df.copy()

    df["總市值(TWD)"] = (
        df["總市值(TWD)"]
        .astype(str)
        .str.replace(",", "", regex=False)
        .replace("", pd.NA)
    )
    df["總市值(TWD)"] = pd.to_numeric(df["總市值(TWD)"], errors="coerce")

    df = df[df["總市值(TWD)"] > 0]
    if df.empty:
        raise ValueError("No rows with 總市值(TWD) > 0")

    return df


def build_sunburst(df: pd.DataFrame):
    fig = px.sunburst(
        df,
        path=["投資地區", "資產類別", "代號"],
        values="總市值(TWD)",
        hover_data={"名稱": True, "總市值(TWD)": ":,.0f"},
    )

    fig.update_layout(
        title="Flow-Analytics｜Sunburst（地區 → 資產 → 個股）",
        margin=dict(t=80, l=20, r=20, b=20),
        font=dict(size=14),
        uniformtext=dict(minsize=10, mode="hide"),
        transition=dict(duration=700, easing="cubic-in-out"),
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


def build_treemap(df: pd.DataFrame):
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

        build_sunburst(df).write_html(str(sunburst_path), include_plotlyjs="cdn")
        build_treemap(df).write_html(str(treemap_path), include_plotlyjs="cdn")

        print("✅ 圖表已生成：outputs/sunburst.html")
        print("✅ 圖表已生成：outputs/treemap.html")
        return 0

    except gspread.exceptions.WorksheetNotFound as error:
        print(f"Error: Worksheet not found: {error}")
    except gspread.exceptions.SpreadsheetNotFound as error:
        print(f"Error: Spreadsheet not found or no access: {error}")
    except gspread.exceptions.APIError as error:
        print(f"Error: Google API error: {error}")
    except FileNotFoundError as error:
        print(f"Error: {error}")
    except ValueError as error:
        print(f"Error: {error}")
    except Exception as error:
        print(f"Unexpected error: {error}")

    return 1


if __name__ == "__main__":
    sys.exit(main())
