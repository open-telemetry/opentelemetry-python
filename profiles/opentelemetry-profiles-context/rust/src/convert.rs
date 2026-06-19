// Copyright The OpenTelemetry Authors
// SPDX-License-Identifier: Apache-2.0

use std::collections::HashMap;

use pyo3::exceptions::PyTypeError;
use pyo3::prelude::*;
use pyo3::types::{PyBool, PyDict, PyFloat, PyInt, PyString};

#[derive(Debug)]
pub enum AttributeValue {
    String(String),
    Bool(bool),
    Int(i64),
    Float(f64),
    StringArray(Vec<String>),
    BoolArray(Vec<bool>),
    IntArray(Vec<i64>),
    FloatArray(Vec<f64>),
}

#[derive(Debug)]
pub struct Resource {
    pub attributes: HashMap<String, AttributeValue>,
    pub schema_url: String,
}

fn attribute_value_from_py(val: &Bound<'_, PyAny>) -> PyResult<AttributeValue> {
    // PyBool must be checked before PyInt: bool is a subclass of int in Python.
    if val.is_instance_of::<PyBool>() {
        return Ok(AttributeValue::Bool(val.extract()?));
    }
    if val.is_instance_of::<PyInt>() {
        return Ok(AttributeValue::Int(val.extract()?));
    }
    if val.is_instance_of::<PyFloat>() {
        return Ok(AttributeValue::Float(val.extract()?));
    }
    if val.is_instance_of::<PyString>() {
        return Ok(AttributeValue::String(val.extract()?));
    }
    // Sequence fallback: collect all elements, dispatch by type of the first.
    let elements: Vec<Bound<'_, PyAny>> = val.try_iter()?.collect::<PyResult<_>>()?;
    if elements.is_empty() {
        return Ok(AttributeValue::StringArray(Vec::new()));
    }
    let first = &elements[0];
    if first.is_instance_of::<PyBool>() {
        return Ok(AttributeValue::BoolArray(
            elements.iter().map(|e| e.extract()).collect::<PyResult<_>>()?,
        ));
    }
    if first.is_instance_of::<PyInt>() {
        return Ok(AttributeValue::IntArray(
            elements.iter().map(|e| e.extract()).collect::<PyResult<_>>()?,
        ));
    }
    if first.is_instance_of::<PyFloat>() {
        return Ok(AttributeValue::FloatArray(
            elements.iter().map(|e| e.extract()).collect::<PyResult<_>>()?,
        ));
    }
    if first.is_instance_of::<PyString>() {
        return Ok(AttributeValue::StringArray(
            elements.iter().map(|e| e.extract()).collect::<PyResult<_>>()?,
        ));
    }
    Err(PyTypeError::new_err(format!(
        "unsupported attribute value type: {}",
        val.get_type().name()?
    )))
}

pub fn resource_from_py(resource: &Bound<'_, PyAny>) -> PyResult<Resource> {
    let py = resource.py();
    let attrs_obj = resource.getattr("attributes")?;

    // Convert BoundedAttributes Mapping → plain dict so PyO3 can unpack it cleanly.
    let py_dict = py
        .import("builtins")?
        .getattr("dict")?
        .call1((&attrs_obj,))?
        .cast_into::<PyDict>()?;

    let mut attributes = HashMap::new();
    for (key, val) in py_dict.iter() {
        attributes.insert(key.extract::<String>()?, attribute_value_from_py(&val)?);
    }

    let schema_url: String = resource.getattr("schema_url")?.extract()?;
    Ok(Resource { attributes, schema_url })
}
