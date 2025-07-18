```{cadquery}
import os
import cadquery as cq

try:
    base = os.path.dirname(__file__)
except NameError:
    # __file__ is not defined in Sphinx executed snippets — fallback
    base = os.path.abspath(".")

step_path = os.path.abspath(os.path.join(base, 'oktavian_a.step'))
print("STEP path:", step_path)

if not os.path.isfile(step_path):
    raise FileNotFoundError(f"STEP file not found: {step_path}")
result = cq.importers.importStep(step_path)
```