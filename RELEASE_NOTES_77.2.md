# WarmLink 77.2 — Generic write handling

- Validate the WarmLink control response for the generic \`warmlink.set_value\` service.
- Do not immediately poll after a control write. The WarmLink cloud/device path can apply writes asynchronously, so an immediate read can return the previous value.
- The normal coordinator polling cycle reconciles the sensor state after the device has applied the change.
