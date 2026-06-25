// Copyright The OpenTelemetry Authors
// SPDX-License-Identifier: Apache-2.0

#![allow(dead_code)]

pub(crate) mod common {
    pub(crate) mod v1 {
        include!("generated/opentelemetry.proto.common.v1.rs");
    }
}

pub(crate) mod resource {
    pub(crate) mod v1 {
        include!("generated/opentelemetry.proto.resource.v1.rs");
    }
}

pub(crate) mod processcontext {
    pub(crate) mod v1development {
        include!("generated/opentelemetry.proto.processcontext.v1development.rs");
    }
}
