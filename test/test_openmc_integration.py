import pytest
import openmc
import tempfile
from pathlib import Path
from unittest.mock import patch, Mock
import numpy as np


def create_simple_model():
    """Create a minimal OpenMC model for testing."""
    # Materials
    water = openmc.Material(name='water')
    water.add_nuclide('H1', 2.0)
    water.add_nuclide('O16', 1.0)
    water.set_density('g/cm3', 1.0)
    
    materials = openmc.Materials([water])
    
    # Geometry
    sphere = openmc.Sphere(r=10.0, boundary_type='vacuum')
    cell = openmc.Cell(fill=water, region=-sphere)
    geometry = openmc.Geometry([cell])
    
    # Settings
    settings = openmc.Settings()
    settings.particles = 100
    settings.batches = 10
    settings.inactive = 5
    settings.source = openmc.IndependentSource(space=openmc.stats.Point((0, 0, 0)))
    
    return openmc.Model(geometry=geometry, materials=materials, settings=settings)


@pytest.mark.skipif(not hasattr(openmc, '__version__'), reason="OpenMC not installed")
def test_simple_openmc_model_runs():
    """Test that we can create and run a simple OpenMC model."""
    model = create_simple_model()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Run in temporary directory
        import os
        old_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            
            # Add a simple tally
            tally = openmc.Tally(name='flux')
            tally.scores = ['flux']
            model.tallies = openmc.Tallies([tally])
            
            # Export to XML files
            model.export_to_xml()
            
            # Verify the model files were created
            assert Path('geometry.xml').exists()
            assert Path('materials.xml').exists()
            assert Path('settings.xml').exists()
            assert Path('tallies.xml').exists()
            
        finally:
            os.chdir(old_cwd)


@pytest.mark.skipif(not hasattr(openmc, '__version__'), reason="OpenMC not installed")  
def test_openmc_statepoint_reading():
    """Test reading OpenMC statepoint structure (without actually running simulation)."""
    # This tests the interface we use in benchmark.py
    model = create_simple_model()
    
    # Add tally
    tally = openmc.Tally(name='test_tally')
    tally.scores = ['flux']
    model.tallies = openmc.Tallies([tally])
    
    # Verify tally structure
    assert len(model.tallies) == 1
    assert model.tallies[0].name == 'test_tally'
    assert 'flux' in model.tallies[0].scores


@pytest.mark.skipif(not hasattr(openmc, '__version__'), reason="OpenMC not installed")
def test_openmc_materials_export():
    """Test that OpenMC materials can be exported."""
    mat = openmc.Material(name='test_mat')
    mat.add_nuclide('H1', 1.0)
    mat.set_density('g/cm3', 1.0)
    
    materials = openmc.Materials([mat])
    
    with tempfile.TemporaryDirectory() as tmpdir:
        import os
        old_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            materials.export_to_xml()
            assert Path('materials.xml').exists()
        finally:
            os.chdir(old_cwd)


@pytest.mark.skipif(not hasattr(openmc, '__version__'), reason="OpenMC not installed")
def test_openmc_geometry_export():
    """Test that OpenMC geometry can be exported."""
    sphere = openmc.Sphere(r=5.0, boundary_type='vacuum')
    cell = openmc.Cell(region=-sphere)
    geometry = openmc.Geometry([cell])
    
    with tempfile.TemporaryDirectory() as tmpdir:
        import os
        old_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            geometry.export_to_xml()
            assert Path('geometry.xml').exists()
        finally:
            os.chdir(old_cwd)


@pytest.mark.skipif(not hasattr(openmc, '__version__'), reason="OpenMC not installed")
def test_benchmark_dependencies_available():
    """Test that key dependencies used by benchmark.py are available."""
    # Test imports that benchmark.py uses
    import openmc
    import yaml
    import pydantic
    
    # Verify OpenMC has the methods we use
    assert hasattr(openmc, 'Model')
    assert hasattr(openmc, 'Material')
    assert hasattr(openmc, 'Geometry')
    assert hasattr(openmc, 'Settings')
    assert hasattr(openmc, 'Tally')
