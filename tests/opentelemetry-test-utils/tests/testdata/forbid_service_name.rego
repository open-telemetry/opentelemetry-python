package live_check_advice

import rego.v1

deny contains result if {
    input.sample.attribute.name == "service.name"
    result := {
        "type":         "advice",
        "advice_type":  "no_service_name",
        "advice_level": "violation",
        "message":      "service.name is forbidden by this policy",
    }
}
