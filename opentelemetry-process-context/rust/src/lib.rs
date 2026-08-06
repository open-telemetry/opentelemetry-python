// Copyright The OpenTelemetry Authors
// SPDX-License-Identifier: Apache-2.0

#[cfg(all(unix, target_has_atomic = "64"))]
mod context;
mod convert;
pub(crate) mod proto;

use pyo3::prelude::*;

#[pyfunction]
#[pyo3(signature = (resource, attributes = None))]
fn publish_context(
    resource: &Bound<'_, PyAny>,
    attributes: Option<&Bound<'_, PyAny>>,
) -> PyResult<()> {
    #[cfg(all(unix, target_has_atomic = "64"))]
    {
        let resource = convert::resource_from_py(resource)?;
        let attributes = match attributes {
            Some(attributes) => convert::key_values_from_py(attributes)?,
            None => Vec::new(),
        };
        context::publish(convert::encode_process_context(resource, attributes))?;
        Ok(())
    }
    #[cfg(not(all(unix, target_has_atomic = "64")))]
    {
        let _ = (resource, attributes);
        Err(pyo3::exceptions::PyRuntimeError::new_err(
            "process context publication requires a Unix-like OS with 64 bit atomic support",
        ))
    }
}

#[pyfunction]
fn unpublish_context() -> PyResult<()> {
    #[cfg(all(unix, target_has_atomic = "64"))]
    {
        context::unpublish()?;
        Ok(())
    }
    #[cfg(not(all(unix, target_has_atomic = "64")))]
    Err(pyo3::exceptions::PyRuntimeError::new_err(
        "process context publication requires a Unix-like OS with 64 bit atomic support",
    ))
}

#[pymodule]
#[pyo3(name = "_rs")]
fn init(_py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_wrapped(wrap_pyfunction!(publish_context))?;
    m.add_wrapped(wrap_pyfunction!(unpublish_context))
}
