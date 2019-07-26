## The base plugin and the normal plugin
There is 7 bases plugins.

### Arch
The most important of all. This plugin is 

### Selector
This plugin allow you to use a query selector to browse the Arch and teirs nodes.

### Input
This plugin handle all kind of input that can happen. The keyboard events, comopositions events,
mouse events). One of it's job is to normalize the inputs for the majors browsers accross a wide
range of devices (including theirs respective virtual keyboards).

### Range
This plugin hold the currently selected text, normalize the selection to be consistent accross
browsers and devices. It provide an API to listen to specific events.

### Renderer
It's job is to render the Arch (see above).

### Rules
This plugin allow to specify rules for the nodes.

### Tests
This plugin allow to test your code. It include helpers method to simulate event on the arch
and nodes.
