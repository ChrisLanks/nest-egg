"""Unit tests for ReportService — date parsing, metrics calculation."""

import pytest
from datetime import date, timedelta

from app.services.report_service import ReportService


svc = ReportService


class TestParseDateRange:
    def test_last_30_days(self):
        start, end = svc._parse_date_range({"type": "preset", "preset": "last_30_days"})
        assert end == date.today()
        assert start == date.today() - timedelta(days=30)

    def test_last_90_days(self):
        start, end = svc._parse_date_range({"type": "preset", "preset": "last_90_days"})
        assert end == date.today()
        assert start == date.today() - timedelta(days=90)

    def test_this_month(self):
        start, end = svc._parse_date_range({"type": "preset", "preset": "this_month"})
        assert start == date(date.today().year, date.today().month, 1)
        assert end == date.today()

    def test_this_year(self):
        start, end = svc._parse_date_range({"type": "preset", "preset": "this_year"})
        assert start == date(date.today().year, 1, 1)
        assert end == date.today()

    def test_last_year(self):
        start, end = svc._parse_date_range({"type": "preset", "preset": "last_year"})
        year = date.today().year - 1
        assert start == date(year, 1, 1)
        assert end == date(year, 12, 31)

    def test_custom_range(self):
        start, end = svc._parse_date_range({
            "type": "custom",
            "startDate": "2024-01-01",
            "endDate": "2024-06-30",
        })
        assert start == date(2024, 1, 1)
        assert end == date(2024, 6, 30)

    def test_default_when_empty(self):
        start, end = svc._parse_date_range({})
        assert end == date.today()
        assert start == date.today() - timedelta(days=30)

    def test_unknown_preset_defaults(self):
        start, end = svc._parse_date_range({"type": "preset", "preset": "unknown"})
        assert end == date.today()


class TestCalculateMetrics:
    def test_sum(self):
        data = [{"amount": 100, "count": 5}, {"amount": 200, "count": 10}]
        result = svc._calculate_metrics(data, ["sum"])
        assert result["total_amount"] == 300

    def test_average(self):
        data = [{"amount": 100, "count": 5}, {"amount": 200, "count": 10}]
        result = svc._calculate_metrics(data, ["average"])
        assert result["average_amount"] == 150.0

    def test_count(self):
        data = [{"amount": 100, "count": 5}, {"amount": 200, "count": 10}]
        result = svc._calculate_metrics(data, ["count"])
        assert result["total_transactions"] == 15
        assert result["total_items"] == 2

    def test_empty_data(self):
        result = svc._calculate_metrics([], ["sum", "average", "count"])
        assert result == {}

    def test_multiple_metrics(self):
        data = [{"amount": 100, "count": 2}]
        result = svc._calculate_metrics(data, ["sum", "average", "count"])
        assert "total_amount" in result
        assert "average_amount" in result
        assert "total_transactions" in result
