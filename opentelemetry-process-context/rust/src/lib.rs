// Copyright The OpenTelemetry Authors
// SPDX-License-Identifier: Apache-2.0

mod convert;
pub(crate) mod proto;
mod publish;

use pyo3::prelude::*;

#[pyfunction]
fn publish_context(resource: &Bound<'_, PyAny>) -> PyResult<()> {
    let _resource = convert::resource_from_py(resource)?;
    // TODO(phase 2): encode the ProcessContext { resource, attributes } payload
    // and publish the real bytes instead of an empty payload.
    publish::publish(&[])?;
    Ok(())
}

#[pyfunction]
fn update_context(resource: &Bound<'_, PyAny>) -> PyResult<()> {
    let _resource = convert::resource_from_py(resource)?;
    // TODO(phase 2): encode the ProcessContext { resource, attributes } payload.
    publish::update(&[])?;
    Ok(())
}

#[pyfunction]
fn unpublish_context() -> PyResult<()> {
    publish::unpublish()?;
    Ok(())
}

#[pymodule]
#[pyo3(name = "_rs")]
fn init(_py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_wrapped(wrap_pyfunction!(publish_context))?;
    m.add_wrapped(wrap_pyfunction!(update_context))?;
    m.add_wrapped(wrap_pyfunction!(unpublish_context))?;
    Ok(())
}
