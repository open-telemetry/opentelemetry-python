package live_check_advice

import rego.v1

deny contains result if {
    input.sample.attribute.name == "never.use.this.attribute"
    result := {
        "type":         "advice",
        "advice_type":  "test_check",
        "advice_level": "violation",
        "context": {
            "attribute_name": input.sample.attribute.name,
        },
        "message":      "never.use.this.attribute is forbidden by this bogus policy",
    }
}
