import pytest
import types
from unittest.mock import patch
from openmc_fusion_benchmarks.uq import (
    get_nuclide_zaid, 
    zaid_to_zam, 
    get_nuclide_gnds,
    get_reaction_mt
)


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


def _fake_openmc_with_data(**data_overrides):
    data = types.SimpleNamespace(zam=fake_zam, gnds_name=fake_gnds_name, REACTION_MT={})
    for key, value in data_overrides.items():
        setattr(data, key, value)
    return types.SimpleNamespace(data=data)


def test_int_input():
    assert get_nuclide_zaid(1001) == 1001


def test_str_input_valid(monkeypatch):
    monkeypatch.setattr('openmc_fusion_benchmarks.uq.uq_utils.openmc', _fake_openmc_with_data(), raising=False)
    assert get_nuclide_zaid('H1') == 1001
    assert get_nuclide_zaid('U238') == 92238


def test_str_input_invalid(monkeypatch):
    monkeypatch.setattr('openmc_fusion_benchmarks.uq.uq_utils.openmc', _fake_openmc_with_data(), raising=False)
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


def fake_gnds_name(z, a, m):
    return f"{'H' if z == 1 else 'U'}{a}"


# Patch globally (or use monkeypatch fixture in pytest)
globals()['zaid_to_zam'] = zaid_to_zam
def _fake_openmc_gnds():
    return types.SimpleNamespace(data=types.SimpleNamespace(gnds_name=fake_gnds_name))


def test_str_input():
    assert get_nuclide_gnds("U235") == "U235"


def test_int_input_valid(monkeypatch):
    monkeypatch.setattr('openmc_fusion_benchmarks.uq.uq_utils.openmc', _fake_openmc_gnds(), raising=False)
    assert get_nuclide_gnds(1001) == "H1"
    assert get_nuclide_gnds(92238) == "U238"


def test_int_input_invalid(monkeypatch):
    def _raise_gnds(_z, _a, _m):
        raise ValueError("Invalid ZAID")

    fake_openmc = types.SimpleNamespace(data=types.SimpleNamespace(gnds_name=_raise_gnds))
    monkeypatch.setattr('openmc_fusion_benchmarks.uq.uq_utils.openmc', fake_openmc, raising=False)
    with pytest.raises(ValueError, match="Invalid ZAID"):
        get_nuclide_gnds(999999)


def test_get_reaction_mt_with_string():
    """Test get_reaction_mt with a reaction name string."""
    fake_openmc = _fake_openmc_with_data(REACTION_MT={'(n,2n)': 16, '(n,gamma)': 102})
    with patch('openmc_fusion_benchmarks.uq.uq_utils.openmc', fake_openmc, create=True):
        from openmc_fusion_benchmarks.uq.uq_utils import get_reaction_mt
        assert get_reaction_mt('(n,2n)') == 16
        assert get_reaction_mt('(n,gamma)') == 102


def test_get_reaction_mt_with_int():
    """Test get_reaction_mt with an MT number directly."""
    fake_openmc = _fake_openmc_with_data(REACTION_MT={})
    with patch('openmc_fusion_benchmarks.uq.uq_utils.openmc', fake_openmc, create=True):
        from openmc_fusion_benchmarks.uq.uq_utils import get_reaction_mt
        assert get_reaction_mt(16) == 16


def test_get_nuclide_gnds_unsupported_type():
    """Test get_nuclide_gnds with unsupported type."""
    with pytest.raises(TypeError, match="Unsupported nuclide type"):
        get_nuclide_gnds([1, 2, 3])
    with pytest.raises(TypeError, match="Unsupported nuclide type"):
        get_nuclide_gnds({'z': 1, 'a': 1})
        assert get_reaction_mt(102) == 102


def test_get_reaction_mt_unknown_reaction():
    """Test get_reaction_mt with unknown reaction returns input."""
    fake_openmc = _fake_openmc_with_data(REACTION_MT={})
    with patch('openmc_fusion_benchmarks.uq.uq_utils.openmc', fake_openmc, create=True):
        from openmc_fusion_benchmarks.uq.uq_utils import get_reaction_mt
        # Unknown reaction should return the input
        assert get_reaction_mt(999) == 999


def test_unsupported_type():
    with pytest.raises(TypeError, match="Unsupported nuclide type"):
        get_nuclide_gnds((1, 1))
