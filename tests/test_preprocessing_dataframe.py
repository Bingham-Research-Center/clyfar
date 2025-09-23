import datetime as dt
import pandas as pd
import pytest


@pytest.mark.filterwarnings("ignore::FutureWarning")
def test_create_forecast_dataframe_from_series():
    # Skip if xarray not available because module imports it at import-time
    pytest.importorskip("xarray")
    from preprocessing.representative_nwp_values import create_forecast_dataframe

    t0 = dt.datetime(2024, 1, 1, 0, 0)
    index = pd.date_range(t0, periods=4, freq="H")
    series = pd.Series([10.0, 12.0, 11.5, 13.0], index=index, name="si10")

    df = create_forecast_dataframe(series, variable_name="si10")
    assert list(df.columns) == ["si10", "fxx"]
    assert df.loc[index[0], "fxx"] == 0
    assert df.loc[index[-1], "fxx"] == 3
    assert df.loc[index[1], "si10"] == 12.0

