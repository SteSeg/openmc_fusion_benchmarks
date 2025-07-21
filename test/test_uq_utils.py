from your_module import get_reaction_mt  # Replace with actual import
from your_module import get_nuclide_gnds  # Replace with your actual module
import pytest
import types
from openmc_fusion_benchmarks.uq import get_nuclide_zaid, zaid_to_zam


def test_zaid_to_zam_len4():
    assert zaid_to_zam(1001) == (1, 1, 0)


def test_zaid_to_zam_len5():
    assert zaid_to_zam(92235) == (92, 235, 0)


def test_zaid_to_zam_len6():
    assert zaid_to_zam(100421) == (100, 42, 1)


def test_invalid_length_raises_valueerror():
    with pytest.raises(ValueError, match="Invalid ZAID length"):
        zaid_to_zam(123)  # Too short
    with pytest.raises(ValueError, match="Invalid ZAID length"):
        zaid_to_zam(1234567)  # Too long


def test_non_integer_input_raises_typeerror():
    with pytest.raises(TypeError, match="ZAID must be an integer"):
        zaid_to_zam("92235")
    with pytest.raises(TypeError, match="ZAID must be an integer"):
        zaid_to_zam(92.235)


def fake_zam(nuclide):
    mapping = {
        'H1': (1, 1, 0),
        'U238': (92, 238, 0),
    }
    if nuclide in mapping:
        return mapping[nuclide]
    raise Exception("Invalid nuclide")


openmc = types.SimpleNamespace(data=types.SimpleNamespace(zam=fake_zam))

# Inject the fake openmc into the global scope of the function
globals()['openmc'] = openmc


def test_int_input():
    assert get_nuclide_zaid(1001) == 1001


def test_str_input_valid():
    assert get_nuclide_zaid('H1') == 1001
    assert get_nuclide_zaid('U238') == 92238


def test_str_input_invalid():
    with pytest.raises(ValueError, match="Invalid GNDS nuclide string"):
        get_nuclide_zaid('X999')


def test_tuple_input_valid():
    assert get_nuclide_zaid((1, 1)) == 1001
    assert get_nuclide_zaid((92, 238, 0)) == 92238


def test_tuple_too_short():
    with pytest.raises(ValueError, match="Tuple must have at least two elements"):
        get_nuclide_zaid((92,))


def test_unsupported_type():
    with pytest.raises(TypeError, match="Unsupported nuclide type"):
        get_nuclide_zaid([92, 238])

# Mock zaid_to_zam and openmc


def fake_zaid_to_zam(zaid):
    mapping = {
        1001: (1, 1, 0),
        92238: (92, 238, 0)
    }
    if zaid in mapping:
        return mapping[zaid]
    raise Exception("Invalid ZAID")


def fake_gnds_name(z, a, m):
    return f"{'H' if z == 1 else 'U'}{a}"


# Patch globally (or use monkeypatch fixture in pytest)
globals()['zaid_to_zam'] = fake_zaid_to_zam
openmc = types.SimpleNamespace(
    data=types.SimpleNamespace(gnds_name=fake_gnds_name))
globals()['openmc'] = openmc


def test_str_input():
    assert get_nuclide_gnds("U235") == "U235"


def test_int_input_valid():
    assert get_nuclide_gnds(1001) == "H1"
    assert get_nuclide_gnds(92238) == "U238"


def test_int_input_invalid():
    with pytest.raises(ValueError, match="Invalid ZAID"):
        get_nuclide_gnds(999999)


def test_unsupported_type():
    with pytest.raises(TypeError, match="Unsupported nuclide type"):
        get_nuclide_gnds((1, 1))
