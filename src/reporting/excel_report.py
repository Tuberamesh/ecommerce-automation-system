import logging
from pathlib import Path

import pandas as pd


logger = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REPORT_PATH = PROJECT_ROOT / "reports" / "ecommerce_report.xlsx"


def _format_workbook(writer: pd.ExcelWriter) -> None:
    for worksheet in writer.book.worksheets:
        worksheet.freeze_panes = "A2"
        if worksheet.max_row and worksheet.max_column:
            worksheet.auto_filter.ref = worksheet.dimensions
        for column_cells in worksheet.columns:
            column_letter = column_cells[0].column_letter
            width = max(
                (len(str(cell.value)) if cell.value is not None else 0)
                for cell in column_cells
            )
            worksheet.column_dimensions[column_letter].width = min(width + 2, 48)


def write_excel_report(
    quality_profile: pd.DataFrame,
    missing_report: pd.DataFrame,
    duplicate_report: pd.DataFrame,
    validation_report: pd.DataFrame,
    analyses: dict[str, pd.DataFrame],
    report_path: Path | str = DEFAULT_REPORT_PATH,
) -> Path:
    path = Path(report_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    sheets = {
        "Data Quality": quality_profile,
        "Missing Values": missing_report,
        "Duplicates": duplicate_report,
        "Validation": validation_report,
        **analyses,
    }

    try:
        with pd.ExcelWriter(path, engine="openpyxl") as writer:
            for sheet_name, frame in sheets.items():
                frame.to_excel(writer, sheet_name=sheet_name[:31], index=False)
            _format_workbook(writer)
    except Exception:
        logger.exception("Could not write Excel report %s", path)
        raise

    logger.info("Excel report written to %s", path)
    return path
