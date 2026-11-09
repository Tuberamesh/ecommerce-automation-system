import pandas as pd
import pytest

from src.cleaning.clean_data_types import clean_data_types
from src.cleaning.handle_duplicates import handle_duplicates
from src.cleaning.handle_missing_values import handle_missing_values
from src.analysis.business_queries import run_business_analysis
from src.database.storage import write_database
from src.ingestion.profile_data import profile_datasets
from src.reporting.excel_report import write_excel_report
from src.transformation.build_analytical_data import build_order_item_fact
from src.validation.validate_data import validate_datasets


def sample_datasets() -> dict[str, pd.DataFrame]:
    return {
        "olist_customers_dataset.csv": pd.DataFrame(
            [
                {
                    "customer_id": "customer-1",
                    "customer_unique_id": "unique-1",
                    "customer_zip_code_prefix": "01000",
                    "customer_city": "city",
                    "customer_state": "SP",
                }
            ]
        ),
        "olist_geolocation_dataset.csv": pd.DataFrame(
            [
                {
                    "geolocation_zip_code_prefix": "01000",
                    "geolocation_lat": -23.5,
                    "geolocation_lng": -46.6,
                    "geolocation_city": "city",
                    "geolocation_state": "SP",
                }
            ]
        ),
        "olist_order_items_dataset.csv": pd.DataFrame(
            [
                {
                    "order_id": "order-1",
                    "order_item_id": 1,
                    "product_id": "product-1",
                    "seller_id": "seller-1",
                    "shipping_limit_date": "2017-01-03",
                    "price": 10.0,
                    "freight_value": 2.0,
                },
                {
                    "order_id": "order-2",
                    "order_item_id": 1,
                    "product_id": "product-1",
                    "seller_id": "seller-1",
                    "shipping_limit_date": "2017-01-04",
                    "price": 20.0,
                    "freight_value": 3.0,
                },
            ]
        ),
        "olist_order_payments_dataset.csv": pd.DataFrame(
            [
                {
                    "order_id": "order-1",
                    "payment_sequential": 1,
                    "payment_type": "credit_card",
                    "payment_installments": 1,
                    "payment_value": 12.0,
                },
                {
                    "order_id": "order-2",
                    "payment_sequential": 1,
                    "payment_type": "credit_card",
                    "payment_installments": 1,
                    "payment_value": 22.0,
                },
            ]
        ),
        "olist_order_reviews_dataset.csv": pd.DataFrame(
            [
                {
                    "review_id": "review-1",
                    "order_id": "order-1",
                    "review_score": 5,
                    "review_comment_title": None,
                    "review_comment_message": None,
                    "review_creation_date": "2017-01-05",
                    "review_answer_timestamp": "2017-01-06",
                }
            ]
        ),
        "olist_orders_dataset.csv": pd.DataFrame(
            [
                {
                    "order_id": "order-1",
                    "customer_id": "customer-1",
                    "order_status": "delivered",
                    "order_purchase_timestamp": "2017-01-01",
                    "order_approved_at": "2017-01-01",
                    "order_delivered_carrier_date": "2017-01-02",
                    "order_delivered_customer_date": "2017-01-04",
                    "order_estimated_delivery_date": "2017-01-10",
                },
                {
                    "order_id": "order-2",
                    "customer_id": "customer-1",
                    "order_status": "canceled",
                    "order_purchase_timestamp": "2017-01-02",
                    "order_approved_at": None,
                    "order_delivered_carrier_date": None,
                    "order_delivered_customer_date": None,
                    "order_estimated_delivery_date": "2017-01-11",
                },
            ]
        ),
        "olist_products_dataset.csv": pd.DataFrame(
            [
                {
                    "product_id": "product-1",
                    "product_category_name": "category",
                    "product_name_lenght": 10,
                    "product_description_lenght": 20,
                    "product_photos_qty": 1,
                    "product_weight_g": 500,
                    "product_length_cm": 10,
                    "product_height_cm": 5,
                    "product_width_cm": 8,
                }
            ]
        ),
        "olist_sellers_dataset.csv": pd.DataFrame(
            [
                {
                    "seller_id": "seller-1",
                    "seller_zip_code_prefix": "02000",
                    "seller_city": "seller city",
                    "seller_state": "SP",
                }
            ]
        ),
        "product_category_name_translation.csv": pd.DataFrame(
            [
                {
                    "product_category_name": "category",
                    "product_category_name_english": "translated category",
                }
            ]
        ),
    }


def test_type_conversion_preserves_missing_zip_and_uses_nullable_integers() -> None:
    zip_codes = pd.DataFrame({"customer_zip_code_prefix": [123, None]})
    converted_zips = clean_data_types(zip_codes, "olist_customers_dataset.csv")
    assert converted_zips["customer_zip_code_prefix"].iloc[0] == "00123"
    assert pd.isna(converted_zips["customer_zip_code_prefix"].iloc[1])

    products = pd.DataFrame(
        {"product_photos_qty": [2.0, None], "product_name_lenght": [10.0, None],
         "product_description_lenght": [20.0, None], "product_weight_g": [300.0, None],
         "product_length_cm": [10.0, None], "product_height_cm": [5.0, None],
         "product_width_cm": [8.0, None]}
    )
    converted_products = clean_data_types(products, "olist_products_dataset.csv")
    assert str(converted_products["product_photos_qty"].dtype) == "Int64"
    assert pd.isna(converted_products["product_photos_qty"].iloc[1])


def test_invalid_nonempty_date_is_not_silently_coerced() -> None:
    orders = pd.DataFrame(
        {
            "order_purchase_timestamp": ["not-a-date"],
            "order_approved_at": [None],
            "order_delivered_carrier_date": [None],
            "order_delivered_customer_date": [None],
            "order_estimated_delivery_date": [None],
        }
    )
    with pytest.raises(ValueError, match="invalid date"):
        clean_data_types(orders, "olist_orders_dataset.csv")


def test_missing_and_duplicate_policies_keep_rows_explicit() -> None:
    missing_data = {
        "olist_order_reviews_dataset.csv": pd.DataFrame(
            {
                "review_comment_title": [" "],
                "review_comment_message": [None],
            }
        )
    }
    normalized, missing_report = handle_missing_values(missing_data)
    assert len(normalized["olist_order_reviews_dataset.csv"]) == 1
    assert int(missing_report["missing_count"].sum()) == 2
    profile = profile_datasets(normalized)
    profile_counts = profile.set_index("column")["missing_count"]
    missing_counts = missing_report.set_index("column")["missing_count"]
    pd.testing.assert_series_equal(
        profile_counts.sort_index(),
        missing_counts.sort_index(),
        check_names=False,
    )
    assert profile["reporting_stage"].nunique() == 1
    assert missing_report["reporting_stage"].nunique() == 1
    assert (
        profile["reporting_stage"].iloc[0]
        == missing_report["reporting_stage"].iloc[0]
    )

    repeated_geo = pd.DataFrame(
        {
            "geolocation_zip_code_prefix": ["01000", "01000"],
            "geolocation_lat": [-23.5, -23.5],
            "geolocation_lng": [-46.6, -46.6],
            "geolocation_city": ["city", "city"],
            "geolocation_state": ["SP", "SP"],
        }
    )
    duplicate_data = {"olist_geolocation_dataset.csv": repeated_geo}
    deduplicated, duplicate_report = handle_duplicates(duplicate_data)
    assert len(deduplicated["olist_geolocation_dataset.csv"]) == 1
    assert duplicate_report.loc[0, "exact_rows_removed"] == 1


def test_standalone_profiling_normalizes_blanks_before_counting(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from src.ingestion import profile_data

    original_profile_datasets = profile_data.profile_datasets
    captured_profiles: list[pd.DataFrame] = []

    def capture_profile(datasets: dict[str, pd.DataFrame]) -> pd.DataFrame:
        profile = original_profile_datasets(datasets)
        captured_profiles.append(profile)
        return profile

    raw_reviews = pd.DataFrame(
        {
            "review_id": ["review-1"],
            "order_id": ["order-1"],
            "review_score": [5],
            "review_comment_title": [" "],
            "review_comment_message": [""],
            "review_creation_date": ["2017-01-05"],
            "review_answer_timestamp": ["2017-01-06"],
        }
    )
    monkeypatch.setattr(
        profile_data,
        "load_all_datasets",
        lambda _path: {"olist_order_reviews_dataset.csv": raw_reviews},
    )
    monkeypatch.setattr(profile_data, "profile_datasets", capture_profile)

    profile_data.main()

    output = capsys.readouterr().out
    assert "Missing-value reporting stage: After type conversion and blank-string normalization" in output
    profile = captured_profiles[0].set_index("column")
    assert profile.loc["review_comment_title", "missing_count"] == 1
    assert profile.loc["review_comment_message", "missing_count"] == 1
    assert profile["reporting_stage"].nunique() == 1


def test_repeated_review_ids_are_reported_but_records_are_retained() -> None:
    reviews = pd.DataFrame(
        {
            "review_id": ["shared-review", "shared-review"],
            "order_id": ["order-1", "order-2"],
            "review_score": [5, 4],
        }
    )
    datasets = {"olist_order_reviews_dataset.csv": reviews}

    cleaned, duplicate_report = handle_duplicates(datasets)
    assert len(cleaned["olist_order_reviews_dataset.csv"]) == 2
    assert duplicate_report.loc[0, "business_key"] == "Not defined"
    assert duplicate_report.loc[0, "business_key_duplicate_rows"] == 0

    validation = validate_datasets(datasets)
    repeated_id = validation.loc[
        validation["rule"].str.startswith("Review ID appears on multiple rows")
    ]
    assert len(repeated_id) == 1
    assert repeated_id.iloc[0]["failed_rows"] == 1
    assert "not assumed duplicates" in repeated_id.iloc[0]["rule"]


def test_database_analysis_and_excel_report_end_to_end(tmp_path) -> None:
    datasets = sample_datasets()
    typed = {
        name: clean_data_types(frame, name)
        for name, frame in datasets.items()
    }
    cleaned, missing_report = handle_missing_values(typed)
    cleaned, duplicate_report = handle_duplicates(cleaned)
    validation = validate_datasets(cleaned)
    assert not validation["status"].eq("ERROR").any()

    fact = build_order_item_fact(cleaned)
    assert len(fact) == len(cleaned["olist_order_items_dataset.csv"])
    assert fact.loc[0, "product_category_name_english"] == "translated category"

    database = write_database(cleaned, fact, tmp_path / "test.db")
    analyses = run_business_analysis(database)
    monthly = analyses["Monthly Sales (Delivered+All)"].iloc[0]
    assert monthly["delivered_order_count"] == 1
    assert monthly["delivered_item_count"] == 1
    assert monthly["delivered_item_revenue"] == 10.0
    assert monthly["delivered_freight"] == 2.0
    assert monthly["delivered_total_value"] == 12.0
    assert monthly["all_status_order_count_with_items"] == 2
    assert monthly["all_status_item_count"] == 2
    assert monthly["all_status_item_value"] == 35.0

    category = analyses["Top Categories (Delivered+All)"].iloc[0]
    assert category["category"] == "translated category"
    assert category["delivered_total_value"] == 12.0
    assert category["all_status_item_value"] == 35.0

    state = analyses["Sales by State (Delivered+All)"].iloc[0]
    assert state["all_status_order_count"] == 2
    assert state["delivered_order_count"] == 1
    assert state["delivered_total_value"] == 12.0
    assert state["all_status_item_value"] == 35.0

    reconciliation = analyses["Payment Reconciliation"].iloc[0]
    assert reconciliation["payment_value_all_statuses"] == 34.0
    assert reconciliation["item_price_total_all_statuses"] == 30.0
    assert reconciliation["freight_total_all_statuses"] == 5.0
    assert reconciliation["item_price_plus_freight_all_statuses"] == 35.0
    assert reconciliation["payment_minus_item_price_and_freight"] == -1.0
    assert "not inherently an error" in reconciliation["interpretation"]

    profile = pd.DataFrame(
        [
            {
                "dataset": "sample.csv",
                "column": "id",
                "data_type": "str",
                "row_count": 1,
                "column_count": 1,
                "missing_count": 0,
                "missing_pct": 0.0,
                "exact_duplicate_rows": 0,
            }
        ]
    )
    report = write_excel_report(
        profile,
        missing_report,
        duplicate_report,
        validation,
        analyses,
        tmp_path / "report.xlsx",
    )
    assert report.is_file()
