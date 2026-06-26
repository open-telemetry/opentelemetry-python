// Copyright The OpenTelemetry Authors
// SPDX-License-Identifier: Apache-2.0

#[cfg(all(unix, target_has_atomic = "64"))]
mod context;
mod convert;
pub(crate) mod proto;

use pyo3::prelude::*;

#[pyfunction]
fn publish_context(resource: &Bound<'_, PyAny>) -> PyResult<()> {
    #[cfg(all(unix, target_has_atomic = "64"))]
    {
        let resource = crate::convert::resource_from_py(resource)?;
        context::publish(crate::convert::encode_process_context(resource))?;
        Ok(())
    }
    #[cfg(not(all(unix, target_has_atomic = "64")))]
    {
        let _ = resource;
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
    #[cfg(all(unix, target_has_atomic = "64"))]
    context::register_fork_handlers();
    m.add_wrapped(wrap_pyfunction!(publish_context))?;
    m.add_wrapped(wrap_pyfunction!(unpublish_context))
}
