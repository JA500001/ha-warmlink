## 77.1 - WarmLink parameter write service

This fork adds a generic `warmlink.set_value` Home Assistant service.

It uses the integration's existing WarmLink control API to write protocol parameters that are already readable by the integration, including H36, compensate_slope and compensate_offset.

Example:

    action:
      - action: warmlink.set_value
        data:
          entity_id: sensor.enable_weather_comp_h36
          code: H36
          value: "1"

      - action: warmlink.set_value
        data:
          entity_id: sensor.weather_comp_slope_compensate_slope
          code: compensate_slope
          value: "0.8"

      - action: warmlink.set_value
        data:
          entity_id: sensor.weather_comp_offset_compensate_offset
          code: compensate_offset
          value: "46"

The entity is used only to locate the WarmLink config entry; the service writes the explicitly supplied protocol code.
