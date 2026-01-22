import sys
from pathlib import Path

from sunburst_utils import build_figure_from_gsheets


OUTPUT_PATH = Path("outputs/sunburst_holdings.html")


def main() -> int:
    try:
        fig = build_figure_from_gsheets()
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        fig.write_html(str(OUTPUT_PATH), include_plotlyjs="cdn")
        print(f"Sunburst chart saved to {OUTPUT_PATH}")
        return 0
    except Exception as error:
        print(f"Error: {error}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
