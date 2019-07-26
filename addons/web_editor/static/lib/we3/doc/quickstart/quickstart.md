# Quickstart
- install the lib
- integrate in your website
- create a plugin
- create a custom arch node
- add a popover

## overview of the architecture

### Loading
- init Editor
- init PluginManager
  - list all dependencies
  - autoinstall all plugin

### when a user send an input

 Event
  ||
  \/
Range --> Plugin --> Arch --> ArchNode
                          <--
                          --> Rules
                          <--
                          --> Render