// Copyright The OpenTelemetry Authors
// SPDX-License-Identifier: Apache-2.0

use crate::proto::common::v1::{any_value, AnyValue, ArrayValue, KeyValue, KeyValueList};
use pyo3::prelude::*;
use pyo3::types::{PyBool, PyDict, PyFloat, PyInt, PyString};

fn any_value_from_py(val: &Bound<'_, PyAny>) -> PyResult<AnyValue> {
    // None -> empty AnyValue (value field absent).
    if val.is_none() {
        return Ok(AnyValue::default());
    }
    // PyBool must be checked before PyInt: bool is a subclass of int in Python.
    if val.is_instance_of::<PyBool>() {
        return Ok(AnyValue { value: Some(any_value::Value::BoolValue(val.extract()?)) });
    }
    if val.is_instance_of::<PyInt>() {
        return Ok(AnyValue { value: Some(any_value::Value::IntValue(val.extract()?)) });
    }
    if val.is_instance_of::<PyFloat>() {
        return Ok(AnyValue { value: Some(any_value::Value::DoubleValue(val.extract()?)) });
    }
    if val.is_instance_of::<PyString>() {
        return Ok(AnyValue { value: Some(any_value::Value::StringValue(val.extract()?)) });
    }
    // Mapping -> KvlistValue. Must come before the sequence fallback because Mappings are iterable.
    let py = val.py();
    let collections_abc = py.import("collections.abc")?;
    if val.is_instance(collections_abc.getattr("Mapping")?.as_ref())? {
        // Normalise arbitrary Mapping to a plain dict first.
        let py_dict = py
            .import("builtins")?
            .getattr("dict")?
            .call1((val,))?
            .cast_into::<PyDict>()?;
        let values = py_dict
            .iter()
            .map(|(k, v)| {
                Ok(KeyValue {
                    key: k.str()?.extract()?,
                    value: Some(any_value_from_py(&v)?),
                    ..Default::default()
                })
            })
            .collect::<PyResult<_>>()?;
        return Ok(AnyValue {
            value: Some(any_value::Value::KvlistValue(KeyValueList { values })),
        });
    }
    // Sequence fallback: recurse per element into ArrayValue.
    let values = val
        .try_iter()?
        .map(|item| any_value_from_py(&item?))
        .collect::<PyResult<_>>()?;
    Ok(AnyValue { value: Some(any_value::Value::ArrayValue(ArrayValue { values })) })
}

pub fn resource_from_py(
    resource: &Bound<'_, PyAny>,
) -> PyResult<crate::proto::resource::v1::Resource> {
    let py = resource.py();
    let attrs_obj = resource.getattr("attributes")?;

    // Convert BoundedAttributes Mapping → plain dict so PyO3 can unpack it cleanly.
    let py_dict = py
        .import("builtins")?
        .getattr("dict")?
        .call1((&attrs_obj,))?
        .cast_into::<PyDict>()?;

    let attributes = py_dict
        .iter()
        .map(|(key, val)| {
            Ok(KeyValue {
                key: key.extract()?,
                value: Some(any_value_from_py(&val)?),
                ..Default::default()
            })
        })
        .collect::<PyResult<_>>()?;

    Ok(crate::proto::resource::v1::Resource {
        attributes,
        ..Default::default()
    })
}
