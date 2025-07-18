```{cadquery}
import os
import cadquery as cq

# Get the path to the file relative to this script
step_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'benchmarks', 'oktavian_a.step'))
result = cq.importers.importStep(step_path)
```