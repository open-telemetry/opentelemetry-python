// Copyright The OpenTelemetry Authors
// SPDX-License-Identifier: Apache-2.0

use std::fs;
use std::path::PathBuf;

use backon::{BlockingRetryable, ExponentialBuilder};

const COMMIT_HASH: &str = "023f8cd36cc946617caa9a9e2e9868186f6d22dd";

const UPSTREAM_PROTOS: &[&str] = &[
    "opentelemetry/proto/common/v1/common.proto",
    "opentelemetry/proto/resource/v1/resource.proto",
    "opentelemetry/proto/processcontext/v1development/process_context.proto",
];

const RAW_BASE: &str =
    "https://raw.githubusercontent.com/open-telemetry/opentelemetry-proto";

fn main() {
    let proto_root = PathBuf::from(std::env::var("OUT_DIR").unwrap()).join("proto");

    for proto_path in UPSTREAM_PROTOS {
        let dest = proto_root.join(proto_path);
        if dest.exists() {
            continue;
        }
        fs::create_dir_all(dest.parent().unwrap()).unwrap();
        let url = format!("{RAW_BASE}/{COMMIT_HASH}/{proto_path}");
        let content = (|| -> Result<String, Box<dyn std::error::Error>> {
            Ok(ureq::get(&url).call()?.into_string()?)
        })
        .retry(ExponentialBuilder::default())
        .call()
        .unwrap();
        fs::write(&dest, content).unwrap();
    }

    let process_context_proto = proto_root
        .join("opentelemetry/proto/processcontext/v1development/process_context.proto");

    prost_build::Config::new()
        .protoc_executable(protoc_bin_vendored::protoc_bin_path().unwrap())
        .compile_protos(&[process_context_proto], &[proto_root])
        .unwrap();
}
