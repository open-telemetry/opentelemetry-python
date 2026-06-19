// Copyright The OpenTelemetry Authors
// SPDX-License-Identifier: Apache-2.0

use pyo3::prelude::*;

#[pyfunction]
fn sum_as_string(a: usize, b: usize) -> PyResult<String> {
    Ok((a + b).to_string())
}

#[pymodule]
#[pyo3(name = "_rs")]
fn init(_py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_wrapped(wrap_pyfunction!(sum_as_string))?;
    Ok(())
}
