from __future__ import absolute_import, division, print_function, unicode_literals

import pytest

from server_common.autosave import (
    AutosaveFile,
    BoolConversion,
    FloatConversion,
    OptionalIntConversion,
)


@pytest.fixture
def autosave_file(tmpdir):
    # for some reason we do actual file i/o in these tests... fine
    yield AutosaveFile(service_name="unittests", file_name="test_file", folder=tmpdir)


def test_GIVEN_no_existing_file_WHEN_get_parameter_from_autosave_THEN_default_returned(
    autosave_file,
):
    default = object()
    assert autosave_file.read_parameter("some_random_parameter", default) == default


def test_GIVEN_parameter_saved_WHEN_get_parameter_from_autosave_THEN_saved_value_returned(
    autosave_file,
):
    value = "test_value"
    autosave_file.write_parameter("parameter", value)
    assert autosave_file.read_parameter("parameter", None) == value


def test_GIVEN_different_parameter_saved_WHEN_get_parameter_from_autosave_THEN_saved_value_returned(
    autosave_file,
):
    value = "test_value"
    autosave_file.write_parameter("other_parameter", value)
    assert autosave_file.read_parameter("parameter", None) is None


def test_GIVEN_parameter_saved_with_different_strategy_WHEN_get_parameter_from_autosave_THEN_saved_value_returned(
    tmpdir,
):
    class Strategy:
        @staticmethod
        def autosave_convert_for_write(values):
            return ",".join([str(value) for value in values])

        @staticmethod
        def autosave_convert_for_read(auto_save_value):
            return [int(i) for i in auto_save_value.split(",")]

    autosave = AutosaveFile(
        service_name="unittests",
        file_name="strat_test_file",
        folder=tmpdir,
        conversion=Strategy(),
    )
    value = [1, 2]
    autosave.write_parameter("parameter_ab", value)
    assert autosave.read_parameter("parameter_ab", None) == value


def test_GIVEN_parameter_saved_as_float_WHEN_get_parameter_from_autosave_THEN_value_returned_as_float(
    tmpdir,
):
    value = 0.173
    key = "parameter"
    autosave = AutosaveFile(
        service_name="unittests",
        file_name="test_file",
        folder=tmpdir,
        conversion=FloatConversion(),
    )

    autosave.write_parameter(key, value)
    result = autosave.read_parameter(key, None)

    assert result == value


def test_GIVEN_parameter_can_not_be_saved_as_float_WHEN_get_parameter_from_autosave_THEN_none_returned(
    tmpdir,
):
    value = "string not a float"
    key = "parameter"
    autosave = AutosaveFile(
        service_name="unittests",
        file_name="test_file",
        folder=tmpdir,
        conversion=FloatConversion(),
    )

    autosave.write_parameter(key, value)
    result = autosave.read_parameter(key, None)

    assert result is None


@pytest.mark.parametrize("value", [True, False])
def test_GIVEN_true_saved_as_bool_WHEN_get_parameter_from_autosave_THEN_value_returned_as_ture(
    tmpdir,
    value,
):
    key = "parameter"
    autosave = AutosaveFile(
        service_name="unittests",
        file_name="test_file",
        folder=tmpdir,
        conversion=BoolConversion(),
    )

    autosave.write_parameter(key, value)
    result = autosave.read_parameter(key, None)

    assert result == value


def test_GIVEN_parameter_can_not_be_saved_as_bool_WHEN_get_parameter_from_autosave_THEN_none_returned(
    tmpdir,
):
    value = "string not a bool"
    key = "parameter"
    autosave = AutosaveFile(
        service_name="unittests",
        file_name="test_file",
        folder=tmpdir,
        conversion=BoolConversion(),
    )

    autosave.write_parameter(key, value)
    result = autosave.read_parameter(key, None)

    assert result is None


@pytest.mark.parametrize("value", [1, None])
def test_GIVEN_int_or_None_WHEN_get_parameter_from_autosave_THEN_value_returned(tmpdir, value):
    key = "parameter"
    autosave = AutosaveFile(
        service_name="unittests",
        file_name="test_file",
        folder=tmpdir,
        conversion=OptionalIntConversion(),
    )

    autosave.write_parameter(key, value)
    result = autosave.read_parameter(key, "not read")

    assert result == value
