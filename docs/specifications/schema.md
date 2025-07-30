# Schema

<div style="display: flex; gap: 1em;">
  <div style="flex: 1;">
    <h4>Version A</h4>
    <div class="highlight highlight-yaml">
      <pre><code class="language-yaml">
geometry:
  file: example_a.step
  mesh:
    max_size: 5.0
      </code></pre>
    </div>
  </div>
  <div style="flex: 1;">
    <h4>Version B</h4>
    <div class="highlight highlight-yaml">
      <pre><code class="language-yaml">
geometry:
  file: example_b.step
  mesh:
    max_size: 10.0
      </code></pre>
    </div>
  </div>
</div>

or

| Version A | Version B |
|-----------|-----------|
| ```yaml
geometry:
  file: example_a.step
  mesh:
    max_size: 5.0
``` | ```yaml
geometry:
  file: example_b.step
  mesh:
    max_size: 10.0
``` |