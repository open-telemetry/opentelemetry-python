// Copyright The OpenTelemetry Authors
// SPDX-License-Identifier: Apache-2.0

mod convert;
pub(crate) mod proto;
mod publish;

use pyo3::prelude::*;
use crate::convert::{encode_process_context, resource_from_py};

#[pyfunction]
fn publish_context(resource: &Bound<'_, PyAny>) -> PyResult<()> {
    let resource = resource_from_py(resource)?;
    publish::publish(encode_process_context(resource))?;
    Ok(())
}

#[pyfunction]
fn update_context(resource: &Bound<'_, PyAny>) -> PyResult<()> {
    let resource = resource_from_py(resource)?;
    publish::update(encode_process_context(resource))?;
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
