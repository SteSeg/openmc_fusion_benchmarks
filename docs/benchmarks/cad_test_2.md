```{cadquery}
import os
import cadquery as cq

step_path = os.path.join(os.path.dirname(__file__), "_static", "oktavian_a.step")
result = cq.importers.importStep(step_path)
```