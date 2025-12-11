# Oktavian Aluminium

Here it is possible to find the analysis of Oktavian aluminum (`oktavian_al`) benchmark run with `ofb`.

## CAD

The following link opens an interactive 3D visualization of the CAD model used in the benchmark:

[View interactive 3D model](https://eepeterson.github.io/openmc_fusion_benchmarks/viewers/oktavian_a.html)

## Results

Results are a set of energy spectra of neutron and photon leaking from the Oktavian aluminum sphere. Figures show energy spectra and C/E values are the ration between every computed value and the experimental value.

### CAD-CSG comparison
Comparison of Experimental, MCNP-CSG, OpenMC-CSG and OpenMC-CAD (from OFB) results for neutron and photon leakage spectra.

<p align="center">
  <img src="images/al_neutron_leakage_csg_cad.svg" width="400" alt="Neutron leakage spectrum">
  <br>
  <em>Figure 2: Neutron leakage spectrum comparison between CAD and CSG geometries.</em>
</p>

<p align="center">
  <img src="images/al_photon_leakage_csg_cad.svg" width="400" alt="Photon leakage spectrum">
  <br>
  <em>Figure 3: Photon leakage spectrum comparison between CAD and CSG geometries.</em>
</p>


### Nuclear Data on CAD analysis
Comparison of ENDF\B-8.0, ENDF\B-8.1, FENDL-3.2b and JEFF-3.3 nuclear data libraries results run with OFB (OpenMC-CAD model) {cite}`brown2018endf80` {cite}`nobre2025endfb8.1` {cite}`schnabel2024fendl` {cite}`plompen2020jeff3.3`. 

<p align="center">
  <img src="images/al_neutron_leakage_nuclear_data.svg" width="400" alt="Neutron leakage spectrum">
  <br>
  <em>Figure 4: Neutron leakage spectrum for different nuclear data libraries using CAD geometry.</em>
</p>

<p align="center">
  <img src="images/al_photon_leakage_nuclear_data.svg" width="400" alt="Photon leakage spectrum">
  <br>
  <em>Figure 5: Photon leakage spectrum for different nuclear data libraries using CAD geometry.</em>
</p>

### Uncertainty Quantification analysis
Total Monte Carlo Uncertainty Quantification (TMC-UQ) results obtained performing 500 perturbations of Al27 cross sections in ENDF\B-8.0 and run the OpenMC CAD model. The center panels and right panels of the two figfures give an insight of statistics at the ~14 MeV energy group for neutrons and ~7.5 MeV energy group for photons.

<p align="center">
  <img src="images/al_neutron_leakage_uq.svg" width="800" alt="Neutron leakage spectrum with uncertainty">
  <br>
  <em>Figure 6: Neutron leakage spectrum with TMC-UQ results.</em>
</p>

<p align="center">
  <img src="images/al_photon_leakage_uq.svg" width="800" alt="Photon leakage spectrum with uncertainty">
  <br>
  <em>Figure 7: Photon leakage spectrum with with TMC-UQ results.</em>
</p>

## References

```{bibliography}