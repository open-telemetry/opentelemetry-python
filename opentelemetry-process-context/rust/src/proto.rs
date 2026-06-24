// Copyright The OpenTelemetry Authors
// SPDX-License-Identifier: Apache-2.0

// The included files are committed, machine-generated prost output produced by the
// maintainer-only `scripts/proto_codegen_process_context.sh` script. They are checked in so that
// building the crate — including building a wheel from the sdist — needs no network
// access and no `protoc`. Relative `include!` paths resolve against this file's
// directory (`src/`). The generated code carries unused message types, so lints are
// silenced on these modules.
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
