// Copyright The OpenTelemetry Authors
// SPDX-License-Identifier: Apache-2.0

pub(crate) mod common {
    pub(crate) mod v1 {
        include!(concat!(env!("OUT_DIR"), "/opentelemetry.proto.common.v1.rs"));
    }
}

pub(crate) mod resource {
    pub(crate) mod v1 {
        include!(concat!(env!("OUT_DIR"), "/opentelemetry.proto.resource.v1.rs"));
    }
}

pub(crate) mod processcontext {
    pub(crate) mod v1development {
        include!(concat!(env!("OUT_DIR"), "/opentelemetry.proto.processcontext.v1development.rs"));
    }
}
