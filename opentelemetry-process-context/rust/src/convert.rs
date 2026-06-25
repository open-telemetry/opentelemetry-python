// Copyright The OpenTelemetry Authors
// SPDX-License-Identifier: Apache-2.0

use crate::proto::common::v1::{AnyValue, ArrayValue, KeyValue, KeyValueList, any_value};
use crate::proto::processcontext::v1development::ProcessContext;
use crate::proto::resource::v1::Resource;
use prost::Message;
use pyo3::exceptions::PyTypeError;
use pyo3::prelude::*;
use pyo3::types::{PyBool, PyDict, PyFloat, PyInt, PyString};

fn any_value_from_py(val: &Bound<'_, PyAny>) -> PyResult<AnyValue> {
    if val.is_none() {
        return Ok(AnyValue::default());
    }
    if val.is_instance_of::<PyBool>() {
        return Ok(AnyValue {
            value: Some(any_value::Value::BoolValue(val.extract()?)),
        });
    }
    if val.is_instance_of::<PyInt>() {
        return Ok(AnyValue {
            value: Some(any_value::Value::IntValue(val.extract()?)),
        });
    }
    if val.is_instance_of::<PyFloat>() {
        return Ok(AnyValue {
            value: Some(any_value::Value::DoubleValue(val.extract()?)),
        });
    }
    if val.is_instance_of::<PyString>() {
        return Ok(AnyValue {
            value: Some(any_value::Value::StringValue(val.extract()?)),
        });
    }

    let py = val.py();
    let collections_abc = py.import("collections.abc")?;

    if val.is_instance(collections_abc.getattr("Mapping")?.as_ref())? {
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

    if val.is_instance(collections_abc.getattr("Sequence")?.as_ref())? {
        let values = val
            .try_iter()?
            .map(|item| any_value_from_py(&item?))
            .collect::<PyResult<_>>()?;
        return Ok(AnyValue {
            value: Some(any_value::Value::ArrayValue(ArrayValue { values })),
        });
    }

    let type_name: String = val.get_type().qualname()?.extract()?;
    Err(PyTypeError::new_err(format!(
        "unsupported attribute value type: {type_name}"
    )))
}

pub fn resource_from_py(resource: &Bound<'_, PyAny>) -> PyResult<Resource> {
    let py = resource.py();
    let attrs_obj = resource.getattr("attributes")?;

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

    Ok(Resource {
        attributes,
        ..Default::default()
    })
}

pub fn encode_process_context(resource: Resource) -> Vec<u8> {
    ProcessContext {
        resource: Some(resource),
        attributes: vec![],
    }
    .encode_to_vec()
}
