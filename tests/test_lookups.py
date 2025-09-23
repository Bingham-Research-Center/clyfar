from utils.lookups import Lookup


def test_lookup_get_key_basic():
    L = Lookup()
    assert L.get_key("snow", "array_name") == "sde"
    assert L.get_key("temp", "gefs_query").startswith("TMP")


def test_lookup_find_vrbl_keys_by_synonym_value():
    L = Lookup()
    # 'sde' should map back to snow dict; 't2m' to temp
    snow_dict = L.find_vrbl_keys("sde")
    temp_dict = L.find_vrbl_keys("t2m")
    assert snow_dict["mf_name"] == "snow"
    assert temp_dict["synoptic"].startswith("temperature")

