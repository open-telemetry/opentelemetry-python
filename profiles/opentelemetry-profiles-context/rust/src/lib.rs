// Copyright The OpenTelemetry Authors
// SPDX-License-Identifier: Apache-2.0

mod convert;
pub(crate) mod proto;

use pyo3::prelude::*;

#[pyfunction]
fn publish_context(resource: &Bound<'_, PyAny>) -> PyResult<()> {
    let _r = convert::resource_from_py(resource)?;
    Ok(())
}

#[pymodule]
#[pyo3(name = "_rs")]
fn init(_py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_wrapped(wrap_pyfunction!(publish_context))?;
    Ok(())
}
