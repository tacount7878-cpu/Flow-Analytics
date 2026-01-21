import os
import sys
from pathlib import Path

import pandas as pd
import gspread

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - fallback for Python < 3.11
    import tomli as tomllib


SECRETS_PATH = Path(".streamlit/secrets.toml")


def load_config() -> dict:
    if SECRETS_PATH.exists():
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
            "source": "secrets.toml",
        }

    return {
        "spreadsheet_id": os.environ.get("GSPREAD_SHEET_ID"),
        "worksheet": os.environ.get("GSPREAD_WORKSHEET", "holdings"),
        "service_account_json_path": os.environ.get(
            "GSPREAD_SERVICE_ACCOUNT_JSON_PATH",
            "data/private/service_account.json",
        ),
        "source": "environment variables",
    }


def validate_config(config: dict) -> None:
    if not config.get("spreadsheet_id"):
        raise ValueError("Missing spreadsheet_id in config.")

    if not config.get("service_account_json_path"):
        raise ValueError("Missing service_account_json_path in config.")


def mask_preview(df: pd.DataFrame) -> pd.DataFrame:
    preview = df.head(3).copy()
    for column in preview.columns:
        preview[column] = "***"
    return preview


def main() -> int:
    try:
        config = load_config()
        validate_config(config)
        service_account_path = Path(config["service_account_json_path"])
        if not service_account_path.exists():
            raise FileNotFoundError(
                f"Service account JSON not found at {service_account_path}"
            )

        client = gspread.service_account(filename=str(service_account_path))
        spreadsheet = client.open_by_key(config["spreadsheet_id"])
        worksheet = spreadsheet.worksheet(config["worksheet"])
        records = worksheet.get_all_records()
        df = pd.DataFrame(records)

        print("Google Sheets smoke test")
        print(f"Config source: {config['source']}")
        print(f"Rows: {len(df)}, Columns: {len(df.columns)}")
        print(f"Columns: {list(df.columns)}")
        if df.empty:
            print("No data returned from worksheet.")
        else:
            masked = mask_preview(df)
            print("Preview (masked):")
            print(masked.to_string(index=False))
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
