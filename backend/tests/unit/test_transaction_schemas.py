"""Unit tests for transaction schema validators and computed fields."""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.transaction import (
    CategoryCreate,
    CategoryResponse,
    CategoryUpdate,
    LabelCreate,
    LabelUpdate,
    ManualTransactionCreate,
    TransactionListResponse,
    TransactionUpdate,
)

# ── CategoryCreate name validator ────────────────────────────────────────────


@pytest.mark.unit
class TestCategoryCreateNameValidator:
    def test_valid_name(self):
        c = CategoryCreate(name="Groceries")
        assert c.name == "Groceries"

    def test_strips_whitespace(self):
        c = CategoryCreate(name="  Groceries  ")
        assert c.name == "Groceries"

    def test_empty_name_raises(self):
        with pytest.raises(ValidationError, match="cannot be empty"):
            CategoryCreate(name="")

    def test_whitespace_only_raises(self):
        with pytest.raises(ValidationError, match="cannot be empty"):
            CategoryCreate(name="   ")

    def test_name_too_long_raises(self):
        with pytest.raises(ValidationError, match="100 characters"):
            CategoryCreate(name="x" * 101)

    def test_name_exactly_100_ok(self):
        c = CategoryCreate(name="x" * 100)
        assert len(c.name) == 100

    def test_angle_brackets_rejected(self):
        with pytest.raises(ValidationError, match="< or >"):
            CategoryCreate(name="<script>")

    def test_gt_bracket_rejected(self):
        with pytest.raises(ValidationError, match="< or >"):
            CategoryCreate(name="foo>bar")


# ── CategoryCreate color validator ───────────────────────────────────────────


@pytest.mark.unit
class TestCategoryCreateColorValidator:
    def test_none_color_ok(self):
        c = CategoryCreate(name="Test", color=None)
        assert c.color is None

    def test_six_char_hex(self):
        c = CategoryCreate(name="Test", color="#FF0000")
        assert c.color == "#FF0000"

    def test_three_char_hex(self):
        c = CategoryCreate(name="Test", color="#F00")
        assert c.color == "#F00"

    def test_no_hash_prefix_added(self):
        c = CategoryCreate(name="Test", color="AABBCC")
        assert c.color == "#AABBCC"

    def test_invalid_hex_raises(self):
        with pytest.raises(ValidationError, match="Color must be valid hex"):
            CategoryCreate(name="Test", color="ZZZZZZ")

    def test_wrong_length_raises(self):
        with pytest.raises(ValidationError, match="Color must be valid hex"):
            CategoryCreate(name="Test", color="#ABCD")

    def test_strips_whitespace_and_hash(self):
        c = CategoryCreate(name="Test", color="  #abc  ")
        assert c.color == "#abc"


# ── CategoryUpdate validators ────────────────────────────────────────────────


@pytest.mark.unit
class TestCategoryUpdateValidators:
    def test_none_name_ok(self):
        u = CategoryUpdate(name=None)
        assert u.name is None

    def test_valid_name(self):
        u = CategoryUpdate(name="Updated")
        assert u.name == "Updated"

    def test_empty_name_raises(self):
        with pytest.raises(ValidationError, match="cannot be empty"):
            CategoryUpdate(name="")

    def test_whitespace_only_raises(self):
        with pytest.raises(ValidationError, match="cannot be empty"):
            CategoryUpdate(name="   ")

    def test_long_name_raises(self):
        with pytest.raises(ValidationError, match="100 characters"):
            CategoryUpdate(name="x" * 101)

    def test_xss_rejected(self):
        with pytest.raises(ValidationError, match="< or >"):
            CategoryUpdate(name="<div>")

    def test_none_color_ok(self):
        u = CategoryUpdate(color=None)
        assert u.color is None

    def test_valid_color(self):
        u = CategoryUpdate(color="#ABC")
        assert u.color == "#ABC"

    def test_invalid_color_raises(self):
        with pytest.raises(ValidationError, match="Color must be valid hex"):
            CategoryUpdate(color="notahex")


# ── LabelCreate validators ───────────────────────────────────────────────────


@pytest.mark.unit
class TestLabelCreateValidators:
    def test_valid_label(self):
        lbl = LabelCreate(name="Income")
        assert lbl.name == "Income"
        assert lbl.is_income is False

    def test_strips_whitespace(self):
        lbl = LabelCreate(name="  Income  ")
        assert lbl.name == "Income"

    def test_empty_name_raises(self):
        with pytest.raises(ValidationError, match="cannot be empty"):
            LabelCreate(name="")

    def test_long_name_raises(self):
        with pytest.raises(ValidationError, match="100 characters"):
            LabelCreate(name="x" * 101)

    def test_angle_brackets_rejected(self):
        with pytest.raises(ValidationError, match="< or >"):
            LabelCreate(name="<b>bold</b>")

    def test_valid_color(self):
        lbl = LabelCreate(name="Test", color="#FF0000")
        assert lbl.color == "#FF0000"

    def test_none_color_ok(self):
        lbl = LabelCreate(name="Test", color=None)
        assert lbl.color is None

    def test_invalid_color_raises(self):
        with pytest.raises(ValidationError, match="Color must be valid hex"):
            LabelCreate(name="Test", color="xyz")


# ── LabelUpdate validators ───────────────────────────────────────────────────


@pytest.mark.unit
class TestLabelUpdateValidators:
    def test_none_name_ok(self):
        u = LabelUpdate(name=None)
        assert u.name is None

    def test_valid_name(self):
        u = LabelUpdate(name="Updated Label")
        assert u.name == "Updated Label"

    def test_empty_name_raises(self):
        with pytest.raises(ValidationError, match="cannot be empty"):
            LabelUpdate(name="")

    def test_whitespace_only_raises(self):
        with pytest.raises(ValidationError, match="cannot be empty"):
            LabelUpdate(name="   ")

    def test_long_name_raises(self):
        with pytest.raises(ValidationError, match="100 characters"):
            LabelUpdate(name="x" * 101)

    def test_xss_rejected(self):
        with pytest.raises(ValidationError, match="< or >"):
            LabelUpdate(name="<script>")

    def test_valid_color(self):
        u = LabelUpdate(color="#abc")
        assert u.color == "#abc"

    def test_invalid_color_raises(self):
        with pytest.raises(ValidationError, match="Color must be valid hex"):
            LabelUpdate(color="nope")

    def test_none_color_ok(self):
        u = LabelUpdate(color=None)
        assert u.color is None


# ── Schema model construction (from_attributes) ─────────────────────────────


@pytest.mark.unit
class TestSchemaConstruction:
    def test_transaction_list_response(self):
        resp = TransactionListResponse(
            transactions=[],
            total=0,
            page=1,
            page_size=25,
            has_more=False,
        )
        assert resp.total == 0
        assert resp.next_cursor is None

    def test_manual_transaction_create(self):
        mt = ManualTransactionCreate(
            date="2024-01-01",
            amount="99.99",
            account_id=uuid4(),
        )
        assert mt.is_pending is False
        assert mt.is_transfer is False

    def test_transaction_update_all_none(self):
        u = TransactionUpdate()
        assert u.merchant_name is None
        assert u.is_transfer is None

    def test_category_response_defaults(self):
        cr = CategoryResponse(
            organization_id=uuid4(),
            name="Test",
        )
        assert cr.is_custom is True
        assert cr.transaction_count == 0
        assert cr.id is None
