import logging
from pathlib import Path

from src.analysis.business_queries import run_business_analysis
from src.cleaning.clean_data_types import clean_data_types
from src.cleaning.handle_duplicates import handle_duplicates
from src.cleaning.handle_missing_values import handle_missing_values
from src.database.storage import DEFAULT_DATABASE_PATH, write_database
from src.ingestion.loader import RAW_DATA_DIR, load_all_datasets
from src.ingestion.profile_data import profile_datasets
from src.logging_config import configure_logging
from src.reporting.excel_report import DEFAULT_REPORT_PATH, write_excel_report
from src.transformation.build_analytical_data import build_order_item_fact
from src.validation.validate_data import validate_datasets


logger = logging.getLogger(__name__)


def run_pipeline(
    raw_data_dir: Path | str = RAW_DATA_DIR,
    database_path: Path | str = DEFAULT_DATABASE_PATH,
    report_path: Path | str = DEFAULT_REPORT_PATH,
) -> Path:
    logger.info("Starting e-commerce data pipeline")
    raw_datasets = load_all_datasets(raw_data_dir)
    typed_datasets = {
        file_name: clean_data_types(df, file_name)
        for file_name, df in raw_datasets.items()
    }
    datasets, missing_report = handle_missing_values(typed_datasets)
    quality_profile = profile_datasets(datasets)
    datasets, duplicate_report = handle_duplicates(datasets)
    validation_report = validate_datasets(datasets)

    errors = validation_report.loc[validation_report["status"] == "ERROR"]
    if not errors.empty:
        failed_rules = errors[["dataset", "rule", "failed_rows"]].to_dict("records")
        raise ValueError(f"Data validation failed; no outputs were written: {failed_rules}")

    order_item_fact = build_order_item_fact(datasets)
    written_database = write_database(datasets, order_item_fact, database_path)
    analyses = run_business_analysis(written_database)
    written_report = write_excel_report(
        quality_profile,
        missing_report,
        duplicate_report,
        validation_report,
        analyses,
        report_path,
    )
    logger.info("Pipeline completed successfully; report: %s", written_report)
    return written_report


def main() -> None:
    configure_logging()
    try:
        run_pipeline()
    except Exception:
        logger.exception("E-commerce data pipeline failed")
        raise


if __name__ == "__main__":
    main()
