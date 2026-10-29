# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

VERSION = "2.22.2"
from decimal import Decimal
from opentelemetry.configuration._validation_exceptions import (
    JsonSchemaValueException,
    JsonSchemaValuesException,
)


NoneType = type(None)

def validate(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data__missing_keys = set(['file_format']) - data.keys()
        if data__missing_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must contain " + str(sorted(data__missing_keys)) + " properties")
        data_keys = set(data.keys())
        if "file_format" in data_keys:
            data_keys.remove("file_format")
            data__fileformat = data["file_format"]
            if not isinstance(data__fileformat, (str)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".file_format must be string")
        if "disabled" in data_keys:
            data_keys.remove("disabled")
            data__disabled = data["disabled"]
            if not isinstance(data__disabled, (bool, NoneType)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".disabled must be boolean or null")
        if "log_level" in data_keys:
            data_keys.remove("log_level")
            data__loglevel = data["log_level"]
            validate____defs_severitynumber(data__loglevel, custom_formats, (name_prefix or "data") + ".log_level")
        if "attribute_limits" in data_keys:
            data_keys.remove("attribute_limits")
            data__attributelimits = data["attribute_limits"]
            validate____defs_attributelimits(data__attributelimits, custom_formats, (name_prefix or "data") + ".attribute_limits")
        if "logger_provider" in data_keys:
            data_keys.remove("logger_provider")
            data__loggerprovider = data["logger_provider"]
            validate____defs_loggerprovider(data__loggerprovider, custom_formats, (name_prefix or "data") + ".logger_provider")
        if "meter_provider" in data_keys:
            data_keys.remove("meter_provider")
            data__meterprovider = data["meter_provider"]
            validate____defs_meterprovider(data__meterprovider, custom_formats, (name_prefix or "data") + ".meter_provider")
        if "propagator" in data_keys:
            data_keys.remove("propagator")
            data__propagator = data["propagator"]
            validate____defs_propagator(data__propagator, custom_formats, (name_prefix or "data") + ".propagator")
        if "tracer_provider" in data_keys:
            data_keys.remove("tracer_provider")
            data__tracerprovider = data["tracer_provider"]
            validate____defs_tracerprovider(data__tracerprovider, custom_formats, (name_prefix or "data") + ".tracer_provider")
        if "resource" in data_keys:
            data_keys.remove("resource")
            data__resource = data["resource"]
            validate____defs_resource(data__resource, custom_formats, (name_prefix or "data") + ".resource")
        if "instrumentation/development" in data_keys:
            data_keys.remove("instrumentation/development")
            data__instrumentationdevelopment = data["instrumentation/development"]
            validate____defs_experimentalinstrumentation(data__instrumentationdevelopment, custom_formats, (name_prefix or "data") + ".instrumentation/development")
        if "distribution" in data_keys:
            data_keys.remove("distribution")
            data__distribution = data["distribution"]
            validate____defs_distribution(data__distribution, custom_formats, (name_prefix or "data") + ".distribution")
    return data

def validate____defs_distribution(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data_len = len(data)
        if data_len < 1:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must contain at least 1 properties")
        data_keys = set(data.keys())
        for data_key in data_keys:
            if data_key not in []:
                data_value = data.get(data_key)
                if not isinstance(data_value, (dict)):
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".{data_key}".format(**locals()) + " must be object")
    return data

def validate____defs_experimentalinstrumentation(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data_keys = set(data.keys())
        if "general" in data_keys:
            data_keys.remove("general")
            data__general = data["general"]
            validate____defs_experimentalgeneralinstrumentation(data__general, custom_formats, (name_prefix or "data") + ".general")
        if "cpp" in data_keys:
            data_keys.remove("cpp")
            data__cpp = data["cpp"]
            validate____defs_experimentallanguagespecificinstrumentation(data__cpp, custom_formats, (name_prefix or "data") + ".cpp")
        if "dotnet" in data_keys:
            data_keys.remove("dotnet")
            data__dotnet = data["dotnet"]
            validate____defs_experimentallanguagespecificinstrumentation(data__dotnet, custom_formats, (name_prefix or "data") + ".dotnet")
        if "erlang" in data_keys:
            data_keys.remove("erlang")
            data__erlang = data["erlang"]
            validate____defs_experimentallanguagespecificinstrumentation(data__erlang, custom_formats, (name_prefix or "data") + ".erlang")
        if "go" in data_keys:
            data_keys.remove("go")
            data__go = data["go"]
            validate____defs_experimentallanguagespecificinstrumentation(data__go, custom_formats, (name_prefix or "data") + ".go")
        if "java" in data_keys:
            data_keys.remove("java")
            data__java = data["java"]
            validate____defs_experimentallanguagespecificinstrumentation(data__java, custom_formats, (name_prefix or "data") + ".java")
        if "js" in data_keys:
            data_keys.remove("js")
            data__js = data["js"]
            validate____defs_experimentallanguagespecificinstrumentation(data__js, custom_formats, (name_prefix or "data") + ".js")
        if "php" in data_keys:
            data_keys.remove("php")
            data__php = data["php"]
            validate____defs_experimentallanguagespecificinstrumentation(data__php, custom_formats, (name_prefix or "data") + ".php")
        if "python" in data_keys:
            data_keys.remove("python")
            data__python = data["python"]
            validate____defs_experimentallanguagespecificinstrumentation(data__python, custom_formats, (name_prefix or "data") + ".python")
        if "ruby" in data_keys:
            data_keys.remove("ruby")
            data__ruby = data["ruby"]
            validate____defs_experimentallanguagespecificinstrumentation(data__ruby, custom_formats, (name_prefix or "data") + ".ruby")
        if "rust" in data_keys:
            data_keys.remove("rust")
            data__rust = data["rust"]
            validate____defs_experimentallanguagespecificinstrumentation(data__rust, custom_formats, (name_prefix or "data") + ".rust")
        if "swift" in data_keys:
            data_keys.remove("swift")
            data__swift = data["swift"]
            validate____defs_experimentallanguagespecificinstrumentation(data__swift, custom_formats, (name_prefix or "data") + ".swift")
        if data_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must not contain "+str(data_keys)+" properties")
    return data

def validate____defs_experimentallanguagespecificinstrumentation(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data_keys = set(data.keys())
        for data_key in data_keys:
            if data_key not in []:
                data_value = data.get(data_key)
                if not isinstance(data_value, (dict)):
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".{data_key}".format(**locals()) + " must be object")
    return data

def validate____defs_experimentalgeneralinstrumentation(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data_keys = set(data.keys())
        if "http" in data_keys:
            data_keys.remove("http")
            data__http = data["http"]
            validate____defs_experimentalhttpinstrumentation(data__http, custom_formats, (name_prefix or "data") + ".http")
        if "code" in data_keys:
            data_keys.remove("code")
            data__code = data["code"]
            validate____defs_experimentalcodeinstrumentation(data__code, custom_formats, (name_prefix or "data") + ".code")
        if "db" in data_keys:
            data_keys.remove("db")
            data__db = data["db"]
            validate____defs_experimentaldbinstrumentation(data__db, custom_formats, (name_prefix or "data") + ".db")
        if "gen_ai" in data_keys:
            data_keys.remove("gen_ai")
            data__genai = data["gen_ai"]
            validate____defs_experimentalgenaiinstrumentation(data__genai, custom_formats, (name_prefix or "data") + ".gen_ai")
        if "messaging" in data_keys:
            data_keys.remove("messaging")
            data__messaging = data["messaging"]
            validate____defs_experimentalmessaginginstrumentation(data__messaging, custom_formats, (name_prefix or "data") + ".messaging")
        if "rpc" in data_keys:
            data_keys.remove("rpc")
            data__rpc = data["rpc"]
            validate____defs_experimentalrpcinstrumentation(data__rpc, custom_formats, (name_prefix or "data") + ".rpc")
        if "sanitization" in data_keys:
            data_keys.remove("sanitization")
            data__sanitization = data["sanitization"]
            validate____defs_experimentalsanitization(data__sanitization, custom_formats, (name_prefix or "data") + ".sanitization")
        if "stability_opt_in_list" in data_keys:
            data_keys.remove("stability_opt_in_list")
            data__stabilityoptinlist = data["stability_opt_in_list"]
            if not isinstance(data__stabilityoptinlist, (str, NoneType)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".stability_opt_in_list must be string or null")
        if data_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must not contain "+str(data_keys)+" properties")
    return data

def validate____defs_experimentalsanitization(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data_keys = set(data.keys())
        if "url" in data_keys:
            data_keys.remove("url")
            data__url = data["url"]
            validate____defs_experimentalurlsanitization(data__url, custom_formats, (name_prefix or "data") + ".url")
        if data_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must not contain "+str(data_keys)+" properties")
    return data

def validate____defs_experimentalurlsanitization(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data_keys = set(data.keys())
        if "sensitive_query_parameters" in data_keys:
            data_keys.remove("sensitive_query_parameters")
            data__sensitivequeryparameters = data["sensitive_query_parameters"]
            if not isinstance(data__sensitivequeryparameters, (list, tuple)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".sensitive_query_parameters must be array")
            data__sensitivequeryparameters_is_list = isinstance(data__sensitivequeryparameters, (list, tuple))
            if data__sensitivequeryparameters_is_list:
                data__sensitivequeryparameters_len = len(data__sensitivequeryparameters)
                if data__sensitivequeryparameters_len < 0:
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".sensitive_query_parameters must contain at least 0 items")
                for data__sensitivequeryparameters_x, data__sensitivequeryparameters_item in enumerate(data__sensitivequeryparameters):
                    if not isinstance(data__sensitivequeryparameters_item, (str)):
                        raise JsonSchemaValueException("" + (name_prefix or "data") + ".sensitive_query_parameters[{data__sensitivequeryparameters_x}]".format(**locals()) + " must be string")
        if data_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must not contain "+str(data_keys)+" properties")
    return data

def validate____defs_experimentalrpcinstrumentation(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data_keys = set(data.keys())
        if "semconv" in data_keys:
            data_keys.remove("semconv")
            data__semconv = data["semconv"]
            validate____defs_experimentalsemconvconfig(data__semconv, custom_formats, (name_prefix or "data") + ".semconv")
        if data_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must not contain "+str(data_keys)+" properties")
    return data

def validate____defs_experimentalsemconvconfig(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data_keys = set(data.keys())
        if "version" in data_keys:
            data_keys.remove("version")
            data__version = data["version"]
            if not isinstance(data__version, (int, NoneType)) and not (isinstance(data__version, float) and data__version.is_integer()) or isinstance(data__version, bool):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".version must be integer or null")
            if isinstance(data__version, (int, float, Decimal)):
                if data__version < 0:
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".version must be bigger than or equal to 0")
        if "experimental" in data_keys:
            data_keys.remove("experimental")
            data__experimental = data["experimental"]
            if not isinstance(data__experimental, (bool, NoneType)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".experimental must be boolean or null")
        if "dual_emit" in data_keys:
            data_keys.remove("dual_emit")
            data__dualemit = data["dual_emit"]
            if not isinstance(data__dualemit, (bool, NoneType)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".dual_emit must be boolean or null")
        if data_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must not contain "+str(data_keys)+" properties")
    return data

def validate____defs_experimentalmessaginginstrumentation(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data_keys = set(data.keys())
        if "semconv" in data_keys:
            data_keys.remove("semconv")
            data__semconv = data["semconv"]
            validate____defs_experimentalsemconvconfig(data__semconv, custom_formats, (name_prefix or "data") + ".semconv")
        if data_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must not contain "+str(data_keys)+" properties")
    return data

def validate____defs_experimentalgenaiinstrumentation(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data_keys = set(data.keys())
        if "semconv" in data_keys:
            data_keys.remove("semconv")
            data__semconv = data["semconv"]
            validate____defs_experimentalsemconvconfig(data__semconv, custom_formats, (name_prefix or "data") + ".semconv")
        if data_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must not contain "+str(data_keys)+" properties")
    return data

def validate____defs_experimentaldbinstrumentation(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data_keys = set(data.keys())
        if "semconv" in data_keys:
            data_keys.remove("semconv")
            data__semconv = data["semconv"]
            validate____defs_experimentalsemconvconfig(data__semconv, custom_formats, (name_prefix or "data") + ".semconv")
        if data_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must not contain "+str(data_keys)+" properties")
    return data

def validate____defs_experimentalcodeinstrumentation(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data_keys = set(data.keys())
        if "semconv" in data_keys:
            data_keys.remove("semconv")
            data__semconv = data["semconv"]
            validate____defs_experimentalsemconvconfig(data__semconv, custom_formats, (name_prefix or "data") + ".semconv")
        if data_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must not contain "+str(data_keys)+" properties")
    return data

def validate____defs_experimentalhttpinstrumentation(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data_keys = set(data.keys())
        if "semconv" in data_keys:
            data_keys.remove("semconv")
            data__semconv = data["semconv"]
            validate____defs_experimentalsemconvconfig(data__semconv, custom_formats, (name_prefix or "data") + ".semconv")
        if "client" in data_keys:
            data_keys.remove("client")
            data__client = data["client"]
            validate____defs_experimentalhttpclientinstrumentation(data__client, custom_formats, (name_prefix or "data") + ".client")
        if "server" in data_keys:
            data_keys.remove("server")
            data__server = data["server"]
            validate____defs_experimentalhttpserverinstrumentation(data__server, custom_formats, (name_prefix or "data") + ".server")
        if data_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must not contain "+str(data_keys)+" properties")
    return data

def validate____defs_experimentalhttpserverinstrumentation(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data_keys = set(data.keys())
        if "request_captured_headers" in data_keys:
            data_keys.remove("request_captured_headers")
            data__requestcapturedheaders = data["request_captured_headers"]
            if not isinstance(data__requestcapturedheaders, (list, tuple)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".request_captured_headers must be array")
            data__requestcapturedheaders_is_list = isinstance(data__requestcapturedheaders, (list, tuple))
            if data__requestcapturedheaders_is_list:
                data__requestcapturedheaders_len = len(data__requestcapturedheaders)
                if data__requestcapturedheaders_len < 1:
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".request_captured_headers must contain at least 1 items")
                for data__requestcapturedheaders_x, data__requestcapturedheaders_item in enumerate(data__requestcapturedheaders):
                    if not isinstance(data__requestcapturedheaders_item, (str)):
                        raise JsonSchemaValueException("" + (name_prefix or "data") + ".request_captured_headers[{data__requestcapturedheaders_x}]".format(**locals()) + " must be string")
        if "response_captured_headers" in data_keys:
            data_keys.remove("response_captured_headers")
            data__responsecapturedheaders = data["response_captured_headers"]
            if not isinstance(data__responsecapturedheaders, (list, tuple)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".response_captured_headers must be array")
            data__responsecapturedheaders_is_list = isinstance(data__responsecapturedheaders, (list, tuple))
            if data__responsecapturedheaders_is_list:
                data__responsecapturedheaders_len = len(data__responsecapturedheaders)
                if data__responsecapturedheaders_len < 1:
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".response_captured_headers must contain at least 1 items")
                for data__responsecapturedheaders_x, data__responsecapturedheaders_item in enumerate(data__responsecapturedheaders):
                    if not isinstance(data__responsecapturedheaders_item, (str)):
                        raise JsonSchemaValueException("" + (name_prefix or "data") + ".response_captured_headers[{data__responsecapturedheaders_x}]".format(**locals()) + " must be string")
        if "known_methods" in data_keys:
            data_keys.remove("known_methods")
            data__knownmethods = data["known_methods"]
            if not isinstance(data__knownmethods, (list, tuple)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".known_methods must be array")
            data__knownmethods_is_list = isinstance(data__knownmethods, (list, tuple))
            if data__knownmethods_is_list:
                data__knownmethods_len = len(data__knownmethods)
                if data__knownmethods_len < 0:
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".known_methods must contain at least 0 items")
                for data__knownmethods_x, data__knownmethods_item in enumerate(data__knownmethods):
                    if not isinstance(data__knownmethods_item, (str)):
                        raise JsonSchemaValueException("" + (name_prefix or "data") + ".known_methods[{data__knownmethods_x}]".format(**locals()) + " must be string")
        if data_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must not contain "+str(data_keys)+" properties")
    return data

def validate____defs_experimentalhttpclientinstrumentation(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data_keys = set(data.keys())
        if "request_captured_headers" in data_keys:
            data_keys.remove("request_captured_headers")
            data__requestcapturedheaders = data["request_captured_headers"]
            if not isinstance(data__requestcapturedheaders, (list, tuple)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".request_captured_headers must be array")
            data__requestcapturedheaders_is_list = isinstance(data__requestcapturedheaders, (list, tuple))
            if data__requestcapturedheaders_is_list:
                data__requestcapturedheaders_len = len(data__requestcapturedheaders)
                if data__requestcapturedheaders_len < 1:
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".request_captured_headers must contain at least 1 items")
                for data__requestcapturedheaders_x, data__requestcapturedheaders_item in enumerate(data__requestcapturedheaders):
                    if not isinstance(data__requestcapturedheaders_item, (str)):
                        raise JsonSchemaValueException("" + (name_prefix or "data") + ".request_captured_headers[{data__requestcapturedheaders_x}]".format(**locals()) + " must be string")
        if "response_captured_headers" in data_keys:
            data_keys.remove("response_captured_headers")
            data__responsecapturedheaders = data["response_captured_headers"]
            if not isinstance(data__responsecapturedheaders, (list, tuple)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".response_captured_headers must be array")
            data__responsecapturedheaders_is_list = isinstance(data__responsecapturedheaders, (list, tuple))
            if data__responsecapturedheaders_is_list:
                data__responsecapturedheaders_len = len(data__responsecapturedheaders)
                if data__responsecapturedheaders_len < 1:
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".response_captured_headers must contain at least 1 items")
                for data__responsecapturedheaders_x, data__responsecapturedheaders_item in enumerate(data__responsecapturedheaders):
                    if not isinstance(data__responsecapturedheaders_item, (str)):
                        raise JsonSchemaValueException("" + (name_prefix or "data") + ".response_captured_headers[{data__responsecapturedheaders_x}]".format(**locals()) + " must be string")
        if "known_methods" in data_keys:
            data_keys.remove("known_methods")
            data__knownmethods = data["known_methods"]
            if not isinstance(data__knownmethods, (list, tuple)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".known_methods must be array")
            data__knownmethods_is_list = isinstance(data__knownmethods, (list, tuple))
            if data__knownmethods_is_list:
                data__knownmethods_len = len(data__knownmethods)
                if data__knownmethods_len < 0:
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".known_methods must contain at least 0 items")
                for data__knownmethods_x, data__knownmethods_item in enumerate(data__knownmethods):
                    if not isinstance(data__knownmethods_item, (str)):
                        raise JsonSchemaValueException("" + (name_prefix or "data") + ".known_methods[{data__knownmethods_x}]".format(**locals()) + " must be string")
        if data_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must not contain "+str(data_keys)+" properties")
    return data

def validate____defs_resource(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data_keys = set(data.keys())
        if "attributes" in data_keys:
            data_keys.remove("attributes")
            data__attributes = data["attributes"]
            if not isinstance(data__attributes, (list, tuple)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".attributes must be array")
            data__attributes_is_list = isinstance(data__attributes, (list, tuple))
            if data__attributes_is_list:
                data__attributes_len = len(data__attributes)
                if data__attributes_len < 1:
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".attributes must contain at least 1 items")
                for data__attributes_x, data__attributes_item in enumerate(data__attributes):
                    validate____defs_attributenamevalue(data__attributes_item, custom_formats, (name_prefix or "data") + ".attributes[{data__attributes_x}]".format(**locals()))
        if "detection/development" in data_keys:
            data_keys.remove("detection/development")
            data__detectiondevelopment = data["detection/development"]
            validate____defs_experimentalresourcedetection(data__detectiondevelopment, custom_formats, (name_prefix or "data") + ".detection/development")
        if "schema_url" in data_keys:
            data_keys.remove("schema_url")
            data__schemaurl = data["schema_url"]
            if not isinstance(data__schemaurl, (str, NoneType)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".schema_url must be string or null")
        if "attributes_list" in data_keys:
            data_keys.remove("attributes_list")
            data__attributeslist = data["attributes_list"]
            if not isinstance(data__attributeslist, (str, NoneType)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".attributes_list must be string or null")
        if data_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must not contain "+str(data_keys)+" properties")
    return data

def validate____defs_experimentalresourcedetection(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data_keys = set(data.keys())
        if "attributes" in data_keys:
            data_keys.remove("attributes")
            data__attributes = data["attributes"]
            validate____defs_includeexclude(data__attributes, custom_formats, (name_prefix or "data") + ".attributes")
        if "detectors" in data_keys:
            data_keys.remove("detectors")
            data__detectors = data["detectors"]
            if not isinstance(data__detectors, (list, tuple)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".detectors must be array")
            data__detectors_is_list = isinstance(data__detectors, (list, tuple))
            if data__detectors_is_list:
                data__detectors_len = len(data__detectors)
                if data__detectors_len < 1:
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".detectors must contain at least 1 items")
                for data__detectors_x, data__detectors_item in enumerate(data__detectors):
                    validate____defs_experimentalresourcedetector(data__detectors_item, custom_formats, (name_prefix or "data") + ".detectors[{data__detectors_x}]".format(**locals()))
        if data_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must not contain "+str(data_keys)+" properties")
    return data

def validate____defs_experimentalresourcedetector(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data_len = len(data)
        if data_len < 1:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must contain at least 1 properties")
        if data_len > 1:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must contain less than or equal to 1 properties")
        data_keys = set(data.keys())
        if "container" in data_keys:
            data_keys.remove("container")
            data__container = data["container"]
            validate____defs_experimentalcontainerresourcedetector(data__container, custom_formats, (name_prefix or "data") + ".container")
        if "host" in data_keys:
            data_keys.remove("host")
            data__host = data["host"]
            validate____defs_experimentalhostresourcedetector(data__host, custom_formats, (name_prefix or "data") + ".host")
        if "process" in data_keys:
            data_keys.remove("process")
            data__process = data["process"]
            validate____defs_experimentalprocessresourcedetector(data__process, custom_formats, (name_prefix or "data") + ".process")
        if "service" in data_keys:
            data_keys.remove("service")
            data__service = data["service"]
            validate____defs_experimentalserviceresourcedetector(data__service, custom_formats, (name_prefix or "data") + ".service")
        for data_key in data_keys:
            if data_key not in ['container', 'host', 'process', 'service']:
                data_value = data.get(data_key)
                if not isinstance(data_value, (dict, NoneType)):
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".{data_key}".format(**locals()) + " must be object or null")
    return data

def validate____defs_experimentalserviceresourcedetector(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict, NoneType)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object or null")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data_keys = set(data.keys())
        if data_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must not contain "+str(data_keys)+" properties")
    return data

def validate____defs_experimentalprocessresourcedetector(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict, NoneType)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object or null")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data_keys = set(data.keys())
        if data_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must not contain "+str(data_keys)+" properties")
    return data

def validate____defs_experimentalhostresourcedetector(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict, NoneType)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object or null")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data_keys = set(data.keys())
        if data_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must not contain "+str(data_keys)+" properties")
    return data

def validate____defs_experimentalcontainerresourcedetector(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict, NoneType)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object or null")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data_keys = set(data.keys())
        if data_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must not contain "+str(data_keys)+" properties")
    return data

def validate____defs_includeexclude(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data_keys = set(data.keys())
        if "included" in data_keys:
            data_keys.remove("included")
            data__included = data["included"]
            if not isinstance(data__included, (list, tuple)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".included must be array")
            data__included_is_list = isinstance(data__included, (list, tuple))
            if data__included_is_list:
                data__included_len = len(data__included)
                if data__included_len < 1:
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".included must contain at least 1 items")
                for data__included_x, data__included_item in enumerate(data__included):
                    if not isinstance(data__included_item, (str)):
                        raise JsonSchemaValueException("" + (name_prefix or "data") + ".included[{data__included_x}]".format(**locals()) + " must be string")
        if "excluded" in data_keys:
            data_keys.remove("excluded")
            data__excluded = data["excluded"]
            if not isinstance(data__excluded, (list, tuple)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".excluded must be array")
            data__excluded_is_list = isinstance(data__excluded, (list, tuple))
            if data__excluded_is_list:
                data__excluded_len = len(data__excluded)
                if data__excluded_len < 1:
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".excluded must contain at least 1 items")
                for data__excluded_x, data__excluded_item in enumerate(data__excluded):
                    if not isinstance(data__excluded_item, (str)):
                        raise JsonSchemaValueException("" + (name_prefix or "data") + ".excluded[{data__excluded_x}]".format(**locals()) + " must be string")
        if data_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must not contain "+str(data_keys)+" properties")
    return data

def validate____defs_attributenamevalue(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data__missing_keys = set(['name', 'value']) - data.keys()
        if data__missing_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must contain " + str(sorted(data__missing_keys)) + " properties")
        data_keys = set(data.keys())
        if "name" in data_keys:
            data_keys.remove("name")
            data__name = data["name"]
            if not isinstance(data__name, (str)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".name must be string")
        if "value" in data_keys:
            data_keys.remove("value")
            data__value = data["value"]
            data__value_one_of_count1 = 0
            if data__value_one_of_count1 < 2:
                try:
                    if not isinstance(data__value, (str)):
                        raise JsonSchemaValueException("" + (name_prefix or "data") + ".value must be string")
                    data__value_one_of_count1 += 1
                except (JsonSchemaValueException, JsonSchemaValuesException): pass
            if data__value_one_of_count1 < 2:
                try:
                    if not isinstance(data__value, (int, float, Decimal)) or isinstance(data__value, bool):
                        raise JsonSchemaValueException("" + (name_prefix or "data") + ".value must be number")
                    data__value_one_of_count1 += 1
                except (JsonSchemaValueException, JsonSchemaValuesException): pass
            if data__value_one_of_count1 < 2:
                try:
                    if not isinstance(data__value, (bool)):
                        raise JsonSchemaValueException("" + (name_prefix or "data") + ".value must be boolean")
                    data__value_one_of_count1 += 1
                except (JsonSchemaValueException, JsonSchemaValuesException): pass
            if data__value_one_of_count1 < 2:
                try:
                    if not isinstance(data__value, (NoneType)):
                        raise JsonSchemaValueException("" + (name_prefix or "data") + ".value must be null")
                    data__value_one_of_count1 += 1
                except (JsonSchemaValueException, JsonSchemaValuesException): pass
            if data__value_one_of_count1 < 2:
                try:
                    if not isinstance(data__value, (list, tuple)):
                        raise JsonSchemaValueException("" + (name_prefix or "data") + ".value must be array")
                    data__value_is_list = isinstance(data__value, (list, tuple))
                    if data__value_is_list:
                        data__value_len = len(data__value)
                        if data__value_len < 1:
                            raise JsonSchemaValueException("" + (name_prefix or "data") + ".value must contain at least 1 items")
                        for data__value_x, data__value_item in enumerate(data__value):
                            if not isinstance(data__value_item, (str)):
                                raise JsonSchemaValueException("" + (name_prefix or "data") + ".value[{data__value_x}]".format(**locals()) + " must be string")
                    data__value_one_of_count1 += 1
                except (JsonSchemaValueException, JsonSchemaValuesException): pass
            if data__value_one_of_count1 < 2:
                try:
                    if not isinstance(data__value, (list, tuple)):
                        raise JsonSchemaValueException("" + (name_prefix or "data") + ".value must be array")
                    data__value_is_list = isinstance(data__value, (list, tuple))
                    if data__value_is_list:
                        data__value_len = len(data__value)
                        if data__value_len < 1:
                            raise JsonSchemaValueException("" + (name_prefix or "data") + ".value must contain at least 1 items")
                        for data__value_x, data__value_item in enumerate(data__value):
                            if not isinstance(data__value_item, (bool)):
                                raise JsonSchemaValueException("" + (name_prefix or "data") + ".value[{data__value_x}]".format(**locals()) + " must be boolean")
                    data__value_one_of_count1 += 1
                except (JsonSchemaValueException, JsonSchemaValuesException): pass
            if data__value_one_of_count1 < 2:
                try:
                    if not isinstance(data__value, (list, tuple)):
                        raise JsonSchemaValueException("" + (name_prefix or "data") + ".value must be array")
                    data__value_is_list = isinstance(data__value, (list, tuple))
                    if data__value_is_list:
                        data__value_len = len(data__value)
                        if data__value_len < 1:
                            raise JsonSchemaValueException("" + (name_prefix or "data") + ".value must contain at least 1 items")
                        for data__value_x, data__value_item in enumerate(data__value):
                            if not isinstance(data__value_item, (int, float, Decimal)) or isinstance(data__value_item, bool):
                                raise JsonSchemaValueException("" + (name_prefix or "data") + ".value[{data__value_x}]".format(**locals()) + " must be number")
                    data__value_one_of_count1 += 1
                except (JsonSchemaValueException, JsonSchemaValuesException): pass
            if data__value_one_of_count1 != 1:
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".value must be valid exactly by one definition")
        if "type" in data_keys:
            data_keys.remove("type")
            data__type = data["type"]
            validate____defs_attributetype(data__type, custom_formats, (name_prefix or "data") + ".type")
        if data_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must not contain "+str(data_keys)+" properties")
    return data

def validate____defs_attributetype(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (str, NoneType)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be string or null")
    if not (isinstance(data, str) and data == 'string' or isinstance(data, str) and data == 'bool' or isinstance(data, str) and data == 'int' or isinstance(data, str) and data == 'double' or isinstance(data, str) and data == 'string_array' or isinstance(data, str) and data == 'bool_array' or isinstance(data, str) and data == 'int_array' or isinstance(data, str) and data == 'double_array'):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be one of ['string', 'bool', 'int', 'double', 'string_array', 'bool_array', 'int_array', 'double_array']")
    return data

def validate____defs_tracerprovider(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data__missing_keys = set(['processors']) - data.keys()
        if data__missing_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must contain " + str(sorted(data__missing_keys)) + " properties")
        data_keys = set(data.keys())
        if "processors" in data_keys:
            data_keys.remove("processors")
            data__processors = data["processors"]
            if not isinstance(data__processors, (list, tuple)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".processors must be array")
            data__processors_is_list = isinstance(data__processors, (list, tuple))
            if data__processors_is_list:
                data__processors_len = len(data__processors)
                if data__processors_len < 1:
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".processors must contain at least 1 items")
                for data__processors_x, data__processors_item in enumerate(data__processors):
                    validate____defs_spanprocessor(data__processors_item, custom_formats, (name_prefix or "data") + ".processors[{data__processors_x}]".format(**locals()))
        if "limits" in data_keys:
            data_keys.remove("limits")
            data__limits = data["limits"]
            validate____defs_spanlimits(data__limits, custom_formats, (name_prefix or "data") + ".limits")
        if "sampler" in data_keys:
            data_keys.remove("sampler")
            data__sampler = data["sampler"]
            validate____defs_sampler(data__sampler, custom_formats, (name_prefix or "data") + ".sampler")
        if "id_generator" in data_keys:
            data_keys.remove("id_generator")
            data__idgenerator = data["id_generator"]
            validate____defs_idgenerator(data__idgenerator, custom_formats, (name_prefix or "data") + ".id_generator")
        if "tracer_configurator/development" in data_keys:
            data_keys.remove("tracer_configurator/development")
            data__tracerconfiguratordevelopment = data["tracer_configurator/development"]
            validate____defs_experimentaltracerconfigurator(data__tracerconfiguratordevelopment, custom_formats, (name_prefix or "data") + ".tracer_configurator/development")
        if data_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must not contain "+str(data_keys)+" properties")
    return data

def validate____defs_experimentaltracerconfigurator(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data_keys = set(data.keys())
        if "default_config" in data_keys:
            data_keys.remove("default_config")
            data__defaultconfig = data["default_config"]
            validate____defs_experimentaltracerconfig(data__defaultconfig, custom_formats, (name_prefix or "data") + ".default_config")
        if "tracers" in data_keys:
            data_keys.remove("tracers")
            data__tracers = data["tracers"]
            if not isinstance(data__tracers, (list, tuple)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".tracers must be array")
            data__tracers_is_list = isinstance(data__tracers, (list, tuple))
            if data__tracers_is_list:
                data__tracers_len = len(data__tracers)
                if data__tracers_len < 1:
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".tracers must contain at least 1 items")
                for data__tracers_x, data__tracers_item in enumerate(data__tracers):
                    validate____defs_experimentaltracermatcherandconfig(data__tracers_item, custom_formats, (name_prefix or "data") + ".tracers[{data__tracers_x}]".format(**locals()))
        if data_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must not contain "+str(data_keys)+" properties")
    return data

def validate____defs_experimentaltracermatcherandconfig(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data__missing_keys = set(['name', 'config']) - data.keys()
        if data__missing_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must contain " + str(sorted(data__missing_keys)) + " properties")
        data_keys = set(data.keys())
        if "name" in data_keys:
            data_keys.remove("name")
            data__name = data["name"]
            if not isinstance(data__name, (str)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".name must be string")
        if "config" in data_keys:
            data_keys.remove("config")
            data__config = data["config"]
            validate____defs_experimentaltracerconfig(data__config, custom_formats, (name_prefix or "data") + ".config")
        if data_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must not contain "+str(data_keys)+" properties")
    return data

def validate____defs_experimentaltracerconfig(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data_keys = set(data.keys())
        if "enabled" in data_keys:
            data_keys.remove("enabled")
            data__enabled = data["enabled"]
            if not isinstance(data__enabled, (bool)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".enabled must be boolean")
        if data_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must not contain "+str(data_keys)+" properties")
    return data

def validate____defs_idgenerator(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data_len = len(data)
        if data_len < 1:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must contain at least 1 properties")
        if data_len > 1:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must contain less than or equal to 1 properties")
        data_keys = set(data.keys())
        if "random" in data_keys:
            data_keys.remove("random")
            data__random = data["random"]
            validate____defs_randomidgenerator(data__random, custom_formats, (name_prefix or "data") + ".random")
        for data_key in data_keys:
            if data_key not in ['random']:
                data_value = data.get(data_key)
                if not isinstance(data_value, (dict, NoneType)):
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".{data_key}".format(**locals()) + " must be object or null")
    return data

def validate____defs_randomidgenerator(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict, NoneType)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object or null")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data_keys = set(data.keys())
        if data_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must not contain "+str(data_keys)+" properties")
    return data

def validate____defs_sampler(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data_len = len(data)
        if data_len < 1:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must contain at least 1 properties")
        if data_len > 1:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must contain less than or equal to 1 properties")
        data_keys = set(data.keys())
        if "always_off" in data_keys:
            data_keys.remove("always_off")
            data__alwaysoff = data["always_off"]
            validate____defs_alwaysoffsampler(data__alwaysoff, custom_formats, (name_prefix or "data") + ".always_off")
        if "always_on" in data_keys:
            data_keys.remove("always_on")
            data__alwayson = data["always_on"]
            validate____defs_alwaysonsampler(data__alwayson, custom_formats, (name_prefix or "data") + ".always_on")
        if "composite/development" in data_keys:
            data_keys.remove("composite/development")
            data__compositedevelopment = data["composite/development"]
            validate____defs_experimentalcomposablesampler(data__compositedevelopment, custom_formats, (name_prefix or "data") + ".composite/development")
        if "jaeger_remote/development" in data_keys:
            data_keys.remove("jaeger_remote/development")
            data__jaegerremotedevelopment = data["jaeger_remote/development"]
            validate____defs_experimentaljaegerremotesampler(data__jaegerremotedevelopment, custom_formats, (name_prefix or "data") + ".jaeger_remote/development")
        if "parent_based" in data_keys:
            data_keys.remove("parent_based")
            data__parentbased = data["parent_based"]
            validate____defs_parentbasedsampler(data__parentbased, custom_formats, (name_prefix or "data") + ".parent_based")
        if "probability/development" in data_keys:
            data_keys.remove("probability/development")
            data__probabilitydevelopment = data["probability/development"]
            validate____defs_experimentalprobabilitysampler(data__probabilitydevelopment, custom_formats, (name_prefix or "data") + ".probability/development")
        if "trace_id_ratio_based" in data_keys:
            data_keys.remove("trace_id_ratio_based")
            data__traceidratiobased = data["trace_id_ratio_based"]
            validate____defs_traceidratiobasedsampler(data__traceidratiobased, custom_formats, (name_prefix or "data") + ".trace_id_ratio_based")
        for data_key in data_keys:
            if data_key not in ['always_off', 'always_on', 'composite/development', 'jaeger_remote/development', 'parent_based', 'probability/development', 'trace_id_ratio_based']:
                data_value = data.get(data_key)
                if not isinstance(data_value, (dict, NoneType)):
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".{data_key}".format(**locals()) + " must be object or null")
    return data

def validate____defs_traceidratiobasedsampler(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict, NoneType)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object or null")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data_keys = set(data.keys())
        if "ratio" in data_keys:
            data_keys.remove("ratio")
            data__ratio = data["ratio"]
            if not isinstance(data__ratio, (int, float, Decimal, NoneType)) or isinstance(data__ratio, bool):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".ratio must be number or null")
            if isinstance(data__ratio, (int, float, Decimal)):
                if data__ratio < 0:
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".ratio must be bigger than or equal to 0")
                if data__ratio > 1:
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".ratio must be smaller than or equal to 1")
        if data_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must not contain "+str(data_keys)+" properties")
    return data

def validate____defs_experimentalprobabilitysampler(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict, NoneType)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object or null")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data_keys = set(data.keys())
        if "ratio" in data_keys:
            data_keys.remove("ratio")
            data__ratio = data["ratio"]
            if not isinstance(data__ratio, (int, float, Decimal, NoneType)) or isinstance(data__ratio, bool):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".ratio must be number or null")
            if isinstance(data__ratio, (int, float, Decimal)):
                if data__ratio < 0:
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".ratio must be bigger than or equal to 0")
                if data__ratio > 1:
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".ratio must be smaller than or equal to 1")
        if data_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must not contain "+str(data_keys)+" properties")
    return data

def validate____defs_parentbasedsampler(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict, NoneType)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object or null")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data_keys = set(data.keys())
        if "root" in data_keys:
            data_keys.remove("root")
            data__root = data["root"]
            validate____defs_sampler(data__root, custom_formats, (name_prefix or "data") + ".root")
        if "remote_parent_sampled" in data_keys:
            data_keys.remove("remote_parent_sampled")
            data__remoteparentsampled = data["remote_parent_sampled"]
            validate____defs_sampler(data__remoteparentsampled, custom_formats, (name_prefix or "data") + ".remote_parent_sampled")
        if "remote_parent_not_sampled" in data_keys:
            data_keys.remove("remote_parent_not_sampled")
            data__remoteparentnotsampled = data["remote_parent_not_sampled"]
            validate____defs_sampler(data__remoteparentnotsampled, custom_formats, (name_prefix or "data") + ".remote_parent_not_sampled")
        if "local_parent_sampled" in data_keys:
            data_keys.remove("local_parent_sampled")
            data__localparentsampled = data["local_parent_sampled"]
            validate____defs_sampler(data__localparentsampled, custom_formats, (name_prefix or "data") + ".local_parent_sampled")
        if "local_parent_not_sampled" in data_keys:
            data_keys.remove("local_parent_not_sampled")
            data__localparentnotsampled = data["local_parent_not_sampled"]
            validate____defs_sampler(data__localparentnotsampled, custom_formats, (name_prefix or "data") + ".local_parent_not_sampled")
        if data_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must not contain "+str(data_keys)+" properties")
    return data

def validate____defs_experimentaljaegerremotesampler(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict, NoneType)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object or null")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data__missing_keys = set(['endpoint', 'initial_sampler']) - data.keys()
        if data__missing_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must contain " + str(sorted(data__missing_keys)) + " properties")
        data_keys = set(data.keys())
        if "endpoint" in data_keys:
            data_keys.remove("endpoint")
            data__endpoint = data["endpoint"]
            if not isinstance(data__endpoint, (str)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".endpoint must be string")
        if "interval" in data_keys:
            data_keys.remove("interval")
            data__interval = data["interval"]
            if not isinstance(data__interval, (int, NoneType)) and not (isinstance(data__interval, float) and data__interval.is_integer()) or isinstance(data__interval, bool):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".interval must be integer or null")
            if isinstance(data__interval, (int, float, Decimal)):
                if data__interval < 0:
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".interval must be bigger than or equal to 0")
        if "initial_sampler" in data_keys:
            data_keys.remove("initial_sampler")
            data__initialsampler = data["initial_sampler"]
            validate____defs_sampler(data__initialsampler, custom_formats, (name_prefix or "data") + ".initial_sampler")
        if data_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must not contain "+str(data_keys)+" properties")
    return data

def validate____defs_experimentalcomposablesampler(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data_len = len(data)
        if data_len < 1:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must contain at least 1 properties")
        if data_len > 1:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must contain less than or equal to 1 properties")
        data_keys = set(data.keys())
        if "always_off" in data_keys:
            data_keys.remove("always_off")
            data__alwaysoff = data["always_off"]
            validate____defs_experimentalcomposablealwaysoffsampler(data__alwaysoff, custom_formats, (name_prefix or "data") + ".always_off")
        if "always_on" in data_keys:
            data_keys.remove("always_on")
            data__alwayson = data["always_on"]
            validate____defs_experimentalcomposablealwaysonsampler(data__alwayson, custom_formats, (name_prefix or "data") + ".always_on")
        if "parent_threshold" in data_keys:
            data_keys.remove("parent_threshold")
            data__parentthreshold = data["parent_threshold"]
            validate____defs_experimentalcomposableparentthresholdsampler(data__parentthreshold, custom_formats, (name_prefix or "data") + ".parent_threshold")
        if "probability" in data_keys:
            data_keys.remove("probability")
            data__probability = data["probability"]
            validate____defs_experimentalcomposableprobabilitysampler(data__probability, custom_formats, (name_prefix or "data") + ".probability")
        if "rule_based" in data_keys:
            data_keys.remove("rule_based")
            data__rulebased = data["rule_based"]
            validate____defs_experimentalcomposablerulebasedsampler(data__rulebased, custom_formats, (name_prefix or "data") + ".rule_based")
        for data_key in data_keys:
            if data_key not in ['always_off', 'always_on', 'parent_threshold', 'probability', 'rule_based']:
                data_value = data.get(data_key)
                if not isinstance(data_value, (dict, NoneType)):
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".{data_key}".format(**locals()) + " must be object or null")
    return data

def validate____defs_experimentalcomposablerulebasedsampler(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict, NoneType)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object or null")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data_keys = set(data.keys())
        if "rules" in data_keys:
            data_keys.remove("rules")
            data__rules = data["rules"]
            if not isinstance(data__rules, (list, tuple)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".rules must be array")
            data__rules_is_list = isinstance(data__rules, (list, tuple))
            if data__rules_is_list:
                data__rules_len = len(data__rules)
                if data__rules_len < 1:
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".rules must contain at least 1 items")
                for data__rules_x, data__rules_item in enumerate(data__rules):
                    validate____defs_experimentalcomposablerulebasedsamplerrule(data__rules_item, custom_formats, (name_prefix or "data") + ".rules[{data__rules_x}]".format(**locals()))
        if data_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must not contain "+str(data_keys)+" properties")
    return data

def validate____defs_experimentalcomposablerulebasedsamplerrule(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data__missing_keys = set(['sampler']) - data.keys()
        if data__missing_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must contain " + str(sorted(data__missing_keys)) + " properties")
        data_keys = set(data.keys())
        if "attribute_values" in data_keys:
            data_keys.remove("attribute_values")
            data__attributevalues = data["attribute_values"]
            validate____defs_experimentalcomposablerulebasedsamplerruleattributevalues(data__attributevalues, custom_formats, (name_prefix or "data") + ".attribute_values")
        if "attribute_patterns" in data_keys:
            data_keys.remove("attribute_patterns")
            data__attributepatterns = data["attribute_patterns"]
            validate____defs_experimentalcomposablerulebasedsamplerruleattributepatterns(data__attributepatterns, custom_formats, (name_prefix or "data") + ".attribute_patterns")
        if "span_kinds" in data_keys:
            data_keys.remove("span_kinds")
            data__spankinds = data["span_kinds"]
            if not isinstance(data__spankinds, (list, tuple)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".span_kinds must be array")
            data__spankinds_is_list = isinstance(data__spankinds, (list, tuple))
            if data__spankinds_is_list:
                data__spankinds_len = len(data__spankinds)
                if data__spankinds_len < 1:
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".span_kinds must contain at least 1 items")
                for data__spankinds_x, data__spankinds_item in enumerate(data__spankinds):
                    validate____defs_spankind(data__spankinds_item, custom_formats, (name_prefix or "data") + ".span_kinds[{data__spankinds_x}]".format(**locals()))
        if "parent" in data_keys:
            data_keys.remove("parent")
            data__parent = data["parent"]
            if not isinstance(data__parent, (list, tuple)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".parent must be array")
            data__parent_is_list = isinstance(data__parent, (list, tuple))
            if data__parent_is_list:
                data__parent_len = len(data__parent)
                if data__parent_len < 1:
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".parent must contain at least 1 items")
                for data__parent_x, data__parent_item in enumerate(data__parent):
                    validate____defs_experimentalspanparent(data__parent_item, custom_formats, (name_prefix or "data") + ".parent[{data__parent_x}]".format(**locals()))
        if "sampler" in data_keys:
            data_keys.remove("sampler")
            data__sampler = data["sampler"]
            validate____defs_experimentalcomposablesampler(data__sampler, custom_formats, (name_prefix or "data") + ".sampler")
        if data_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must not contain "+str(data_keys)+" properties")
    return data

def validate____defs_experimentalspanparent(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (str, NoneType)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be string or null")
    if not (isinstance(data, str) and data == 'none' or isinstance(data, str) and data == 'remote' or isinstance(data, str) and data == 'local'):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be one of ['none', 'remote', 'local']")
    return data

def validate____defs_spankind(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (str, NoneType)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be string or null")
    if not (isinstance(data, str) and data == 'internal' or isinstance(data, str) and data == 'server' or isinstance(data, str) and data == 'client' or isinstance(data, str) and data == 'producer' or isinstance(data, str) and data == 'consumer'):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be one of ['internal', 'server', 'client', 'producer', 'consumer']")
    return data

def validate____defs_experimentalcomposablerulebasedsamplerruleattributepatterns(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data__missing_keys = set(['key']) - data.keys()
        if data__missing_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must contain " + str(sorted(data__missing_keys)) + " properties")
        data_keys = set(data.keys())
        if "key" in data_keys:
            data_keys.remove("key")
            data__key = data["key"]
            if not isinstance(data__key, (str)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".key must be string")
        if "included" in data_keys:
            data_keys.remove("included")
            data__included = data["included"]
            if not isinstance(data__included, (list, tuple)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".included must be array")
            data__included_is_list = isinstance(data__included, (list, tuple))
            if data__included_is_list:
                data__included_len = len(data__included)
                if data__included_len < 1:
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".included must contain at least 1 items")
                for data__included_x, data__included_item in enumerate(data__included):
                    if not isinstance(data__included_item, (str)):
                        raise JsonSchemaValueException("" + (name_prefix or "data") + ".included[{data__included_x}]".format(**locals()) + " must be string")
        if "excluded" in data_keys:
            data_keys.remove("excluded")
            data__excluded = data["excluded"]
            if not isinstance(data__excluded, (list, tuple)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".excluded must be array")
            data__excluded_is_list = isinstance(data__excluded, (list, tuple))
            if data__excluded_is_list:
                data__excluded_len = len(data__excluded)
                if data__excluded_len < 1:
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".excluded must contain at least 1 items")
                for data__excluded_x, data__excluded_item in enumerate(data__excluded):
                    if not isinstance(data__excluded_item, (str)):
                        raise JsonSchemaValueException("" + (name_prefix or "data") + ".excluded[{data__excluded_x}]".format(**locals()) + " must be string")
        if data_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must not contain "+str(data_keys)+" properties")
    return data

def validate____defs_experimentalcomposablerulebasedsamplerruleattributevalues(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data__missing_keys = set(['key', 'values']) - data.keys()
        if data__missing_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must contain " + str(sorted(data__missing_keys)) + " properties")
        data_keys = set(data.keys())
        if "key" in data_keys:
            data_keys.remove("key")
            data__key = data["key"]
            if not isinstance(data__key, (str)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".key must be string")
        if "values" in data_keys:
            data_keys.remove("values")
            data__values = data["values"]
            if not isinstance(data__values, (list, tuple)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".values must be array")
            data__values_is_list = isinstance(data__values, (list, tuple))
            if data__values_is_list:
                data__values_len = len(data__values)
                if data__values_len < 1:
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".values must contain at least 1 items")
                for data__values_x, data__values_item in enumerate(data__values):
                    if not isinstance(data__values_item, (str)):
                        raise JsonSchemaValueException("" + (name_prefix or "data") + ".values[{data__values_x}]".format(**locals()) + " must be string")
        if data_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must not contain "+str(data_keys)+" properties")
    return data

def validate____defs_experimentalcomposableprobabilitysampler(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict, NoneType)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object or null")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data_keys = set(data.keys())
        if "ratio" in data_keys:
            data_keys.remove("ratio")
            data__ratio = data["ratio"]
            if not isinstance(data__ratio, (int, float, Decimal, NoneType)) or isinstance(data__ratio, bool):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".ratio must be number or null")
            if isinstance(data__ratio, (int, float, Decimal)):
                if data__ratio < 0:
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".ratio must be bigger than or equal to 0")
                if data__ratio > 1:
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".ratio must be smaller than or equal to 1")
        if data_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must not contain "+str(data_keys)+" properties")
    return data

def validate____defs_experimentalcomposableparentthresholdsampler(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data__missing_keys = set(['root']) - data.keys()
        if data__missing_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must contain " + str(sorted(data__missing_keys)) + " properties")
        data_keys = set(data.keys())
        if "root" in data_keys:
            data_keys.remove("root")
            data__root = data["root"]
            validate____defs_experimentalcomposablesampler(data__root, custom_formats, (name_prefix or "data") + ".root")
        if data_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must not contain "+str(data_keys)+" properties")
    return data

def validate____defs_experimentalcomposablealwaysonsampler(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict, NoneType)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object or null")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data_keys = set(data.keys())
        if data_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must not contain "+str(data_keys)+" properties")
    return data

def validate____defs_experimentalcomposablealwaysoffsampler(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict, NoneType)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object or null")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data_keys = set(data.keys())
        if data_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must not contain "+str(data_keys)+" properties")
    return data

def validate____defs_alwaysonsampler(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict, NoneType)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object or null")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data_keys = set(data.keys())
        if data_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must not contain "+str(data_keys)+" properties")
    return data

def validate____defs_alwaysoffsampler(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict, NoneType)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object or null")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data_keys = set(data.keys())
        if data_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must not contain "+str(data_keys)+" properties")
    return data

def validate____defs_spanlimits(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data_keys = set(data.keys())
        if "attribute_value_length_limit" in data_keys:
            data_keys.remove("attribute_value_length_limit")
            data__attributevaluelengthlimit = data["attribute_value_length_limit"]
            if not isinstance(data__attributevaluelengthlimit, (int, NoneType)) and not (isinstance(data__attributevaluelengthlimit, float) and data__attributevaluelengthlimit.is_integer()) or isinstance(data__attributevaluelengthlimit, bool):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".attribute_value_length_limit must be integer or null")
            if isinstance(data__attributevaluelengthlimit, (int, float, Decimal)):
                if data__attributevaluelengthlimit < 0:
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".attribute_value_length_limit must be bigger than or equal to 0")
        if "attribute_count_limit" in data_keys:
            data_keys.remove("attribute_count_limit")
            data__attributecountlimit = data["attribute_count_limit"]
            if not isinstance(data__attributecountlimit, (int, NoneType)) and not (isinstance(data__attributecountlimit, float) and data__attributecountlimit.is_integer()) or isinstance(data__attributecountlimit, bool):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".attribute_count_limit must be integer or null")
            if isinstance(data__attributecountlimit, (int, float, Decimal)):
                if data__attributecountlimit < 0:
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".attribute_count_limit must be bigger than or equal to 0")
        if "event_count_limit" in data_keys:
            data_keys.remove("event_count_limit")
            data__eventcountlimit = data["event_count_limit"]
            if not isinstance(data__eventcountlimit, (int, NoneType)) and not (isinstance(data__eventcountlimit, float) and data__eventcountlimit.is_integer()) or isinstance(data__eventcountlimit, bool):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".event_count_limit must be integer or null")
            if isinstance(data__eventcountlimit, (int, float, Decimal)):
                if data__eventcountlimit < 0:
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".event_count_limit must be bigger than or equal to 0")
        if "link_count_limit" in data_keys:
            data_keys.remove("link_count_limit")
            data__linkcountlimit = data["link_count_limit"]
            if not isinstance(data__linkcountlimit, (int, NoneType)) and not (isinstance(data__linkcountlimit, float) and data__linkcountlimit.is_integer()) or isinstance(data__linkcountlimit, bool):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".link_count_limit must be integer or null")
            if isinstance(data__linkcountlimit, (int, float, Decimal)):
                if data__linkcountlimit < 0:
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".link_count_limit must be bigger than or equal to 0")
        if "event_attribute_count_limit" in data_keys:
            data_keys.remove("event_attribute_count_limit")
            data__eventattributecountlimit = data["event_attribute_count_limit"]
            if not isinstance(data__eventattributecountlimit, (int, NoneType)) and not (isinstance(data__eventattributecountlimit, float) and data__eventattributecountlimit.is_integer()) or isinstance(data__eventattributecountlimit, bool):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".event_attribute_count_limit must be integer or null")
            if isinstance(data__eventattributecountlimit, (int, float, Decimal)):
                if data__eventattributecountlimit < 0:
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".event_attribute_count_limit must be bigger than or equal to 0")
        if "link_attribute_count_limit" in data_keys:
            data_keys.remove("link_attribute_count_limit")
            data__linkattributecountlimit = data["link_attribute_count_limit"]
            if not isinstance(data__linkattributecountlimit, (int, NoneType)) and not (isinstance(data__linkattributecountlimit, float) and data__linkattributecountlimit.is_integer()) or isinstance(data__linkattributecountlimit, bool):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".link_attribute_count_limit must be integer or null")
            if isinstance(data__linkattributecountlimit, (int, float, Decimal)):
                if data__linkattributecountlimit < 0:
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".link_attribute_count_limit must be bigger than or equal to 0")
        if data_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must not contain "+str(data_keys)+" properties")
    return data

def validate____defs_spanprocessor(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data_len = len(data)
        if data_len < 1:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must contain at least 1 properties")
        if data_len > 1:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must contain less than or equal to 1 properties")
        data_keys = set(data.keys())
        if "batch" in data_keys:
            data_keys.remove("batch")
            data__batch = data["batch"]
            validate____defs_batchspanprocessor(data__batch, custom_formats, (name_prefix or "data") + ".batch")
        if "simple" in data_keys:
            data_keys.remove("simple")
            data__simple = data["simple"]
            validate____defs_simplespanprocessor(data__simple, custom_formats, (name_prefix or "data") + ".simple")
        for data_key in data_keys:
            if data_key not in ['batch', 'simple']:
                data_value = data.get(data_key)
                if not isinstance(data_value, (dict, NoneType)):
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".{data_key}".format(**locals()) + " must be object or null")
    return data

def validate____defs_simplespanprocessor(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data__missing_keys = set(['exporter']) - data.keys()
        if data__missing_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must contain " + str(sorted(data__missing_keys)) + " properties")
        data_keys = set(data.keys())
        if "exporter" in data_keys:
            data_keys.remove("exporter")
            data__exporter = data["exporter"]
            validate____defs_spanexporter(data__exporter, custom_formats, (name_prefix or "data") + ".exporter")
        if data_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must not contain "+str(data_keys)+" properties")
    return data

def validate____defs_spanexporter(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data_len = len(data)
        if data_len < 1:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must contain at least 1 properties")
        if data_len > 1:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must contain less than or equal to 1 properties")
        data_keys = set(data.keys())
        if "otlp_http" in data_keys:
            data_keys.remove("otlp_http")
            data__otlphttp = data["otlp_http"]
            validate____defs_otlphttpexporter(data__otlphttp, custom_formats, (name_prefix or "data") + ".otlp_http")
        if "otlp_grpc" in data_keys:
            data_keys.remove("otlp_grpc")
            data__otlpgrpc = data["otlp_grpc"]
            validate____defs_otlpgrpcexporter(data__otlpgrpc, custom_formats, (name_prefix or "data") + ".otlp_grpc")
        if "otlp_file/development" in data_keys:
            data_keys.remove("otlp_file/development")
            data__otlpfiledevelopment = data["otlp_file/development"]
            validate____defs_experimentalotlpfileexporter(data__otlpfiledevelopment, custom_formats, (name_prefix or "data") + ".otlp_file/development")
        if "console" in data_keys:
            data_keys.remove("console")
            data__console = data["console"]
            validate____defs_consoleexporter(data__console, custom_formats, (name_prefix or "data") + ".console")
        for data_key in data_keys:
            if data_key not in ['otlp_http', 'otlp_grpc', 'otlp_file/development', 'console']:
                data_value = data.get(data_key)
                if not isinstance(data_value, (dict, NoneType)):
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".{data_key}".format(**locals()) + " must be object or null")
    return data

def validate____defs_consoleexporter(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict, NoneType)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object or null")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data_keys = set(data.keys())
        if data_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must not contain "+str(data_keys)+" properties")
    return data

def validate____defs_experimentalotlpfileexporter(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict, NoneType)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object or null")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data_keys = set(data.keys())
        if "output_stream" in data_keys:
            data_keys.remove("output_stream")
            data__outputstream = data["output_stream"]
            if not isinstance(data__outputstream, (str, NoneType)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".output_stream must be string or null")
        if data_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must not contain "+str(data_keys)+" properties")
    return data

def validate____defs_otlpgrpcexporter(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict, NoneType)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object or null")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data_keys = set(data.keys())
        if "endpoint" in data_keys:
            data_keys.remove("endpoint")
            data__endpoint = data["endpoint"]
            if not isinstance(data__endpoint, (str, NoneType)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".endpoint must be string or null")
        if "tls" in data_keys:
            data_keys.remove("tls")
            data__tls = data["tls"]
            validate____defs_grpctls(data__tls, custom_formats, (name_prefix or "data") + ".tls")
        if "headers" in data_keys:
            data_keys.remove("headers")
            data__headers = data["headers"]
            if not isinstance(data__headers, (list, tuple)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".headers must be array")
            data__headers_is_list = isinstance(data__headers, (list, tuple))
            if data__headers_is_list:
                data__headers_len = len(data__headers)
                if data__headers_len < 1:
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".headers must contain at least 1 items")
                for data__headers_x, data__headers_item in enumerate(data__headers):
                    validate____defs_namestringvaluepair(data__headers_item, custom_formats, (name_prefix or "data") + ".headers[{data__headers_x}]".format(**locals()))
        if "headers_list" in data_keys:
            data_keys.remove("headers_list")
            data__headerslist = data["headers_list"]
            if not isinstance(data__headerslist, (str, NoneType)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".headers_list must be string or null")
        if "compression" in data_keys:
            data_keys.remove("compression")
            data__compression = data["compression"]
            if not isinstance(data__compression, (str, NoneType)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".compression must be string or null")
        if "timeout" in data_keys:
            data_keys.remove("timeout")
            data__timeout = data["timeout"]
            if not isinstance(data__timeout, (int, NoneType)) and not (isinstance(data__timeout, float) and data__timeout.is_integer()) or isinstance(data__timeout, bool):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".timeout must be integer or null")
            if isinstance(data__timeout, (int, float, Decimal)):
                if data__timeout < 0:
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".timeout must be bigger than or equal to 0")
        if data_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must not contain "+str(data_keys)+" properties")
    return data

def validate____defs_namestringvaluepair(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data__missing_keys = set(['name', 'value']) - data.keys()
        if data__missing_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must contain " + str(sorted(data__missing_keys)) + " properties")
        data_keys = set(data.keys())
        if "name" in data_keys:
            data_keys.remove("name")
            data__name = data["name"]
            if not isinstance(data__name, (str)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".name must be string")
        if "value" in data_keys:
            data_keys.remove("value")
            data__value = data["value"]
            if not isinstance(data__value, (str, NoneType)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".value must be string or null")
        if data_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must not contain "+str(data_keys)+" properties")
    return data

def validate____defs_grpctls(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict, NoneType)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object or null")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data_keys = set(data.keys())
        if "ca_file" in data_keys:
            data_keys.remove("ca_file")
            data__cafile = data["ca_file"]
            if not isinstance(data__cafile, (str, NoneType)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".ca_file must be string or null")
        if "key_file" in data_keys:
            data_keys.remove("key_file")
            data__keyfile = data["key_file"]
            if not isinstance(data__keyfile, (str, NoneType)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".key_file must be string or null")
        if "cert_file" in data_keys:
            data_keys.remove("cert_file")
            data__certfile = data["cert_file"]
            if not isinstance(data__certfile, (str, NoneType)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".cert_file must be string or null")
        if "insecure" in data_keys:
            data_keys.remove("insecure")
            data__insecure = data["insecure"]
            if not isinstance(data__insecure, (bool, NoneType)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".insecure must be boolean or null")
        if data_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must not contain "+str(data_keys)+" properties")
    return data

def validate____defs_otlphttpexporter(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict, NoneType)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object or null")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data_keys = set(data.keys())
        if "endpoint" in data_keys:
            data_keys.remove("endpoint")
            data__endpoint = data["endpoint"]
            if not isinstance(data__endpoint, (str, NoneType)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".endpoint must be string or null")
        if "tls" in data_keys:
            data_keys.remove("tls")
            data__tls = data["tls"]
            validate____defs_httptls(data__tls, custom_formats, (name_prefix or "data") + ".tls")
        if "headers" in data_keys:
            data_keys.remove("headers")
            data__headers = data["headers"]
            if not isinstance(data__headers, (list, tuple)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".headers must be array")
            data__headers_is_list = isinstance(data__headers, (list, tuple))
            if data__headers_is_list:
                data__headers_len = len(data__headers)
                if data__headers_len < 1:
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".headers must contain at least 1 items")
                for data__headers_x, data__headers_item in enumerate(data__headers):
                    validate____defs_namestringvaluepair(data__headers_item, custom_formats, (name_prefix or "data") + ".headers[{data__headers_x}]".format(**locals()))
        if "headers_list" in data_keys:
            data_keys.remove("headers_list")
            data__headerslist = data["headers_list"]
            if not isinstance(data__headerslist, (str, NoneType)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".headers_list must be string or null")
        if "compression" in data_keys:
            data_keys.remove("compression")
            data__compression = data["compression"]
            if not isinstance(data__compression, (str, NoneType)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".compression must be string or null")
        if "timeout" in data_keys:
            data_keys.remove("timeout")
            data__timeout = data["timeout"]
            if not isinstance(data__timeout, (int, NoneType)) and not (isinstance(data__timeout, float) and data__timeout.is_integer()) or isinstance(data__timeout, bool):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".timeout must be integer or null")
            if isinstance(data__timeout, (int, float, Decimal)):
                if data__timeout < 0:
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".timeout must be bigger than or equal to 0")
        if "encoding" in data_keys:
            data_keys.remove("encoding")
            data__encoding = data["encoding"]
            validate____defs_otlphttpencoding(data__encoding, custom_formats, (name_prefix or "data") + ".encoding")
        if data_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must not contain "+str(data_keys)+" properties")
    return data

def validate____defs_otlphttpencoding(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (str, NoneType)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be string or null")
    if not (isinstance(data, str) and data == 'protobuf' or isinstance(data, str) and data == 'json'):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be one of ['protobuf', 'json']")
    return data

def validate____defs_httptls(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict, NoneType)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object or null")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data_keys = set(data.keys())
        if "ca_file" in data_keys:
            data_keys.remove("ca_file")
            data__cafile = data["ca_file"]
            if not isinstance(data__cafile, (str, NoneType)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".ca_file must be string or null")
        if "key_file" in data_keys:
            data_keys.remove("key_file")
            data__keyfile = data["key_file"]
            if not isinstance(data__keyfile, (str, NoneType)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".key_file must be string or null")
        if "cert_file" in data_keys:
            data_keys.remove("cert_file")
            data__certfile = data["cert_file"]
            if not isinstance(data__certfile, (str, NoneType)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".cert_file must be string or null")
        if data_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must not contain "+str(data_keys)+" properties")
    return data

def validate____defs_batchspanprocessor(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data__missing_keys = set(['exporter']) - data.keys()
        if data__missing_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must contain " + str(sorted(data__missing_keys)) + " properties")
        data_keys = set(data.keys())
        if "schedule_delay" in data_keys:
            data_keys.remove("schedule_delay")
            data__scheduledelay = data["schedule_delay"]
            if not isinstance(data__scheduledelay, (int, NoneType)) and not (isinstance(data__scheduledelay, float) and data__scheduledelay.is_integer()) or isinstance(data__scheduledelay, bool):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".schedule_delay must be integer or null")
            if isinstance(data__scheduledelay, (int, float, Decimal)):
                if data__scheduledelay < 0:
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".schedule_delay must be bigger than or equal to 0")
        if "export_timeout" in data_keys:
            data_keys.remove("export_timeout")
            data__exporttimeout = data["export_timeout"]
            if not isinstance(data__exporttimeout, (int, NoneType)) and not (isinstance(data__exporttimeout, float) and data__exporttimeout.is_integer()) or isinstance(data__exporttimeout, bool):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".export_timeout must be integer or null")
            if isinstance(data__exporttimeout, (int, float, Decimal)):
                if data__exporttimeout < 0:
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".export_timeout must be bigger than or equal to 0")
        if "max_queue_size" in data_keys:
            data_keys.remove("max_queue_size")
            data__maxqueuesize = data["max_queue_size"]
            if not isinstance(data__maxqueuesize, (int, NoneType)) and not (isinstance(data__maxqueuesize, float) and data__maxqueuesize.is_integer()) or isinstance(data__maxqueuesize, bool):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".max_queue_size must be integer or null")
            if isinstance(data__maxqueuesize, (int, float, Decimal)):
                if data__maxqueuesize <= 0:
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".max_queue_size must be bigger than 0")
        if "max_export_batch_size" in data_keys:
            data_keys.remove("max_export_batch_size")
            data__maxexportbatchsize = data["max_export_batch_size"]
            if not isinstance(data__maxexportbatchsize, (int, NoneType)) and not (isinstance(data__maxexportbatchsize, float) and data__maxexportbatchsize.is_integer()) or isinstance(data__maxexportbatchsize, bool):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".max_export_batch_size must be integer or null")
            if isinstance(data__maxexportbatchsize, (int, float, Decimal)):
                if data__maxexportbatchsize <= 0:
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".max_export_batch_size must be bigger than 0")
        if "exporter" in data_keys:
            data_keys.remove("exporter")
            data__exporter = data["exporter"]
            validate____defs_spanexporter(data__exporter, custom_formats, (name_prefix or "data") + ".exporter")
        if data_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must not contain "+str(data_keys)+" properties")
    return data

def validate____defs_propagator(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data_keys = set(data.keys())
        if "composite" in data_keys:
            data_keys.remove("composite")
            data__composite = data["composite"]
            if not isinstance(data__composite, (list, tuple)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".composite must be array")
            data__composite_is_list = isinstance(data__composite, (list, tuple))
            if data__composite_is_list:
                data__composite_len = len(data__composite)
                if data__composite_len < 1:
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".composite must contain at least 1 items")
                for data__composite_x, data__composite_item in enumerate(data__composite):
                    validate____defs_textmappropagator(data__composite_item, custom_formats, (name_prefix or "data") + ".composite[{data__composite_x}]".format(**locals()))
        if "composite_list" in data_keys:
            data_keys.remove("composite_list")
            data__compositelist = data["composite_list"]
            if not isinstance(data__compositelist, (str, NoneType)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".composite_list must be string or null")
        if data_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must not contain "+str(data_keys)+" properties")
    return data

def validate____defs_textmappropagator(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data_len = len(data)
        if data_len < 1:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must contain at least 1 properties")
        if data_len > 1:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must contain less than or equal to 1 properties")
        data_keys = set(data.keys())
        if "tracecontext" in data_keys:
            data_keys.remove("tracecontext")
            data__tracecontext = data["tracecontext"]
            validate____defs_tracecontextpropagator(data__tracecontext, custom_formats, (name_prefix or "data") + ".tracecontext")
        if "baggage" in data_keys:
            data_keys.remove("baggage")
            data__baggage = data["baggage"]
            validate____defs_baggagepropagator(data__baggage, custom_formats, (name_prefix or "data") + ".baggage")
        if "b3" in data_keys:
            data_keys.remove("b3")
            data__b3 = data["b3"]
            validate____defs_b3propagator(data__b3, custom_formats, (name_prefix or "data") + ".b3")
        if "b3multi" in data_keys:
            data_keys.remove("b3multi")
            data__b3multi = data["b3multi"]
            validate____defs_b3multipropagator(data__b3multi, custom_formats, (name_prefix or "data") + ".b3multi")
        for data_key in data_keys:
            if data_key not in ['tracecontext', 'baggage', 'b3', 'b3multi']:
                data_value = data.get(data_key)
                if not isinstance(data_value, (dict, NoneType)):
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".{data_key}".format(**locals()) + " must be object or null")
    return data

def validate____defs_b3multipropagator(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict, NoneType)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object or null")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data_keys = set(data.keys())
        if data_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must not contain "+str(data_keys)+" properties")
    return data

def validate____defs_b3propagator(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict, NoneType)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object or null")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data_keys = set(data.keys())
        if data_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must not contain "+str(data_keys)+" properties")
    return data

def validate____defs_baggagepropagator(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict, NoneType)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object or null")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data_keys = set(data.keys())
        if data_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must not contain "+str(data_keys)+" properties")
    return data

def validate____defs_tracecontextpropagator(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict, NoneType)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object or null")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data_keys = set(data.keys())
        if data_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must not contain "+str(data_keys)+" properties")
    return data

def validate____defs_meterprovider(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data__missing_keys = set(['readers']) - data.keys()
        if data__missing_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must contain " + str(sorted(data__missing_keys)) + " properties")
        data_keys = set(data.keys())
        if "readers" in data_keys:
            data_keys.remove("readers")
            data__readers = data["readers"]
            if not isinstance(data__readers, (list, tuple)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".readers must be array")
            data__readers_is_list = isinstance(data__readers, (list, tuple))
            if data__readers_is_list:
                data__readers_len = len(data__readers)
                if data__readers_len < 1:
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".readers must contain at least 1 items")
                for data__readers_x, data__readers_item in enumerate(data__readers):
                    validate____defs_metricreader(data__readers_item, custom_formats, (name_prefix or "data") + ".readers[{data__readers_x}]".format(**locals()))
        if "views" in data_keys:
            data_keys.remove("views")
            data__views = data["views"]
            if not isinstance(data__views, (list, tuple)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".views must be array")
            data__views_is_list = isinstance(data__views, (list, tuple))
            if data__views_is_list:
                data__views_len = len(data__views)
                if data__views_len < 1:
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".views must contain at least 1 items")
                for data__views_x, data__views_item in enumerate(data__views):
                    validate____defs_view(data__views_item, custom_formats, (name_prefix or "data") + ".views[{data__views_x}]".format(**locals()))
        if "exemplar_filter" in data_keys:
            data_keys.remove("exemplar_filter")
            data__exemplarfilter = data["exemplar_filter"]
            validate____defs_exemplarfilter(data__exemplarfilter, custom_formats, (name_prefix or "data") + ".exemplar_filter")
        if "meter_configurator/development" in data_keys:
            data_keys.remove("meter_configurator/development")
            data__meterconfiguratordevelopment = data["meter_configurator/development"]
            validate____defs_experimentalmeterconfigurator(data__meterconfiguratordevelopment, custom_formats, (name_prefix or "data") + ".meter_configurator/development")
        if data_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must not contain "+str(data_keys)+" properties")
    return data

def validate____defs_experimentalmeterconfigurator(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data_keys = set(data.keys())
        if "default_config" in data_keys:
            data_keys.remove("default_config")
            data__defaultconfig = data["default_config"]
            validate____defs_experimentalmeterconfig(data__defaultconfig, custom_formats, (name_prefix or "data") + ".default_config")
        if "meters" in data_keys:
            data_keys.remove("meters")
            data__meters = data["meters"]
            if not isinstance(data__meters, (list, tuple)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".meters must be array")
            data__meters_is_list = isinstance(data__meters, (list, tuple))
            if data__meters_is_list:
                data__meters_len = len(data__meters)
                if data__meters_len < 1:
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".meters must contain at least 1 items")
                for data__meters_x, data__meters_item in enumerate(data__meters):
                    validate____defs_experimentalmetermatcherandconfig(data__meters_item, custom_formats, (name_prefix or "data") + ".meters[{data__meters_x}]".format(**locals()))
        if data_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must not contain "+str(data_keys)+" properties")
    return data

def validate____defs_experimentalmetermatcherandconfig(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data__missing_keys = set(['name', 'config']) - data.keys()
        if data__missing_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must contain " + str(sorted(data__missing_keys)) + " properties")
        data_keys = set(data.keys())
        if "name" in data_keys:
            data_keys.remove("name")
            data__name = data["name"]
            if not isinstance(data__name, (str)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".name must be string")
        if "config" in data_keys:
            data_keys.remove("config")
            data__config = data["config"]
            validate____defs_experimentalmeterconfig(data__config, custom_formats, (name_prefix or "data") + ".config")
        if data_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must not contain "+str(data_keys)+" properties")
    return data

def validate____defs_experimentalmeterconfig(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data_keys = set(data.keys())
        if "enabled" in data_keys:
            data_keys.remove("enabled")
            data__enabled = data["enabled"]
            if not isinstance(data__enabled, (bool)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".enabled must be boolean")
        if data_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must not contain "+str(data_keys)+" properties")
    return data

def validate____defs_exemplarfilter(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (str, NoneType)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be string or null")
    if not (isinstance(data, str) and data == 'always_on' or isinstance(data, str) and data == 'always_off' or isinstance(data, str) and data == 'trace_based'):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be one of ['always_on', 'always_off', 'trace_based']")
    return data

def validate____defs_view(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data__missing_keys = set(['selector', 'stream']) - data.keys()
        if data__missing_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must contain " + str(sorted(data__missing_keys)) + " properties")
        data_keys = set(data.keys())
        if "selector" in data_keys:
            data_keys.remove("selector")
            data__selector = data["selector"]
            validate____defs_viewselector(data__selector, custom_formats, (name_prefix or "data") + ".selector")
        if "stream" in data_keys:
            data_keys.remove("stream")
            data__stream = data["stream"]
            validate____defs_viewstream(data__stream, custom_formats, (name_prefix or "data") + ".stream")
        if data_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must not contain "+str(data_keys)+" properties")
    return data

def validate____defs_viewstream(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data_keys = set(data.keys())
        if "name" in data_keys:
            data_keys.remove("name")
            data__name = data["name"]
            if not isinstance(data__name, (str, NoneType)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".name must be string or null")
        if "description" in data_keys:
            data_keys.remove("description")
            data__description = data["description"]
            if not isinstance(data__description, (str, NoneType)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".description must be string or null")
        if "aggregation" in data_keys:
            data_keys.remove("aggregation")
            data__aggregation = data["aggregation"]
            validate____defs_aggregation(data__aggregation, custom_formats, (name_prefix or "data") + ".aggregation")
        if "aggregation_cardinality_limit" in data_keys:
            data_keys.remove("aggregation_cardinality_limit")
            data__aggregationcardinalitylimit = data["aggregation_cardinality_limit"]
            if not isinstance(data__aggregationcardinalitylimit, (int, NoneType)) and not (isinstance(data__aggregationcardinalitylimit, float) and data__aggregationcardinalitylimit.is_integer()) or isinstance(data__aggregationcardinalitylimit, bool):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".aggregation_cardinality_limit must be integer or null")
            if isinstance(data__aggregationcardinalitylimit, (int, float, Decimal)):
                if data__aggregationcardinalitylimit <= 0:
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".aggregation_cardinality_limit must be bigger than 0")
        if "attribute_keys" in data_keys:
            data_keys.remove("attribute_keys")
            data__attributekeys = data["attribute_keys"]
            validate____defs_includeexclude(data__attributekeys, custom_formats, (name_prefix or "data") + ".attribute_keys")
        if data_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must not contain "+str(data_keys)+" properties")
    return data

def validate____defs_aggregation(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data_len = len(data)
        if data_len < 1:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must contain at least 1 properties")
        if data_len > 1:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must contain less than or equal to 1 properties")
        data_keys = set(data.keys())
        if "default" in data_keys:
            data_keys.remove("default")
            data__default = data["default"]
            validate____defs_defaultaggregation(data__default, custom_formats, (name_prefix or "data") + ".default")
        if "drop" in data_keys:
            data_keys.remove("drop")
            data__drop = data["drop"]
            validate____defs_dropaggregation(data__drop, custom_formats, (name_prefix or "data") + ".drop")
        if "explicit_bucket_histogram" in data_keys:
            data_keys.remove("explicit_bucket_histogram")
            data__explicitbuckethistogram = data["explicit_bucket_histogram"]
            validate____defs_explicitbuckethistogramaggregation(data__explicitbuckethistogram, custom_formats, (name_prefix or "data") + ".explicit_bucket_histogram")
        if "base2_exponential_bucket_histogram" in data_keys:
            data_keys.remove("base2_exponential_bucket_histogram")
            data__base2exponentialbuckethistogram = data["base2_exponential_bucket_histogram"]
            validate____defs_base2exponentialbuckethistogramaggregation(data__base2exponentialbuckethistogram, custom_formats, (name_prefix or "data") + ".base2_exponential_bucket_histogram")
        if "last_value" in data_keys:
            data_keys.remove("last_value")
            data__lastvalue = data["last_value"]
            validate____defs_lastvalueaggregation(data__lastvalue, custom_formats, (name_prefix or "data") + ".last_value")
        if "sum" in data_keys:
            data_keys.remove("sum")
            data__sum = data["sum"]
            validate____defs_sumaggregation(data__sum, custom_formats, (name_prefix or "data") + ".sum")
        if data_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must not contain "+str(data_keys)+" properties")
    return data

def validate____defs_sumaggregation(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict, NoneType)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object or null")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data_keys = set(data.keys())
        if data_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must not contain "+str(data_keys)+" properties")
    return data

def validate____defs_lastvalueaggregation(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict, NoneType)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object or null")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data_keys = set(data.keys())
        if data_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must not contain "+str(data_keys)+" properties")
    return data

def validate____defs_base2exponentialbuckethistogramaggregation(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict, NoneType)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object or null")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data_keys = set(data.keys())
        if "max_scale" in data_keys:
            data_keys.remove("max_scale")
            data__maxscale = data["max_scale"]
            if not isinstance(data__maxscale, (int, NoneType)) and not (isinstance(data__maxscale, float) and data__maxscale.is_integer()) or isinstance(data__maxscale, bool):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".max_scale must be integer or null")
            if isinstance(data__maxscale, (int, float, Decimal)):
                if data__maxscale < -10:
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".max_scale must be bigger than or equal to -10")
                if data__maxscale > 20:
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".max_scale must be smaller than or equal to 20")
        if "max_size" in data_keys:
            data_keys.remove("max_size")
            data__maxsize = data["max_size"]
            if not isinstance(data__maxsize, (int, NoneType)) and not (isinstance(data__maxsize, float) and data__maxsize.is_integer()) or isinstance(data__maxsize, bool):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".max_size must be integer or null")
            if isinstance(data__maxsize, (int, float, Decimal)):
                if data__maxsize < 2:
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".max_size must be bigger than or equal to 2")
        if "record_min_max" in data_keys:
            data_keys.remove("record_min_max")
            data__recordminmax = data["record_min_max"]
            if not isinstance(data__recordminmax, (bool, NoneType)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".record_min_max must be boolean or null")
        if data_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must not contain "+str(data_keys)+" properties")
    return data

def validate____defs_explicitbuckethistogramaggregation(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict, NoneType)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object or null")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data_keys = set(data.keys())
        if "boundaries" in data_keys:
            data_keys.remove("boundaries")
            data__boundaries = data["boundaries"]
            if not isinstance(data__boundaries, (list, tuple)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".boundaries must be array")
            data__boundaries_is_list = isinstance(data__boundaries, (list, tuple))
            if data__boundaries_is_list:
                data__boundaries_len = len(data__boundaries)
                if data__boundaries_len < 0:
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".boundaries must contain at least 0 items")
                for data__boundaries_x, data__boundaries_item in enumerate(data__boundaries):
                    if not isinstance(data__boundaries_item, (int, float, Decimal)) or isinstance(data__boundaries_item, bool):
                        raise JsonSchemaValueException("" + (name_prefix or "data") + ".boundaries[{data__boundaries_x}]".format(**locals()) + " must be number")
        if "record_min_max" in data_keys:
            data_keys.remove("record_min_max")
            data__recordminmax = data["record_min_max"]
            if not isinstance(data__recordminmax, (bool, NoneType)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".record_min_max must be boolean or null")
        if data_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must not contain "+str(data_keys)+" properties")
    return data

def validate____defs_dropaggregation(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict, NoneType)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object or null")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data_keys = set(data.keys())
        if data_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must not contain "+str(data_keys)+" properties")
    return data

def validate____defs_defaultaggregation(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict, NoneType)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object or null")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data_keys = set(data.keys())
        if data_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must not contain "+str(data_keys)+" properties")
    return data

def validate____defs_viewselector(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data_keys = set(data.keys())
        if "instrument_name" in data_keys:
            data_keys.remove("instrument_name")
            data__instrumentname = data["instrument_name"]
            if not isinstance(data__instrumentname, (str, NoneType)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".instrument_name must be string or null")
        if "instrument_type" in data_keys:
            data_keys.remove("instrument_type")
            data__instrumenttype = data["instrument_type"]
            validate____defs_instrumenttype(data__instrumenttype, custom_formats, (name_prefix or "data") + ".instrument_type")
        if "unit" in data_keys:
            data_keys.remove("unit")
            data__unit = data["unit"]
            if not isinstance(data__unit, (str, NoneType)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".unit must be string or null")
        if "meter_name" in data_keys:
            data_keys.remove("meter_name")
            data__metername = data["meter_name"]
            if not isinstance(data__metername, (str, NoneType)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".meter_name must be string or null")
        if "meter_version" in data_keys:
            data_keys.remove("meter_version")
            data__meterversion = data["meter_version"]
            if not isinstance(data__meterversion, (str, NoneType)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".meter_version must be string or null")
        if "meter_schema_url" in data_keys:
            data_keys.remove("meter_schema_url")
            data__meterschemaurl = data["meter_schema_url"]
            if not isinstance(data__meterschemaurl, (str, NoneType)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".meter_schema_url must be string or null")
        if data_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must not contain "+str(data_keys)+" properties")
    return data

def validate____defs_instrumenttype(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (str, NoneType)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be string or null")
    if not (isinstance(data, str) and data == 'counter' or isinstance(data, str) and data == 'gauge' or isinstance(data, str) and data == 'histogram' or isinstance(data, str) and data == 'observable_counter' or isinstance(data, str) and data == 'observable_gauge' or isinstance(data, str) and data == 'observable_up_down_counter' or isinstance(data, str) and data == 'up_down_counter'):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be one of ['counter', 'gauge', 'histogram', 'observable_counter', 'observable_gauge', 'observable_up_down_counter', 'up_down_counter']")
    return data

def validate____defs_metricreader(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data_len = len(data)
        if data_len < 1:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must contain at least 1 properties")
        if data_len > 1:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must contain less than or equal to 1 properties")
        data_keys = set(data.keys())
        if "periodic" in data_keys:
            data_keys.remove("periodic")
            data__periodic = data["periodic"]
            validate____defs_periodicmetricreader(data__periodic, custom_formats, (name_prefix or "data") + ".periodic")
        if "pull" in data_keys:
            data_keys.remove("pull")
            data__pull = data["pull"]
            validate____defs_pullmetricreader(data__pull, custom_formats, (name_prefix or "data") + ".pull")
        if data_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must not contain "+str(data_keys)+" properties")
    return data

def validate____defs_pullmetricreader(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data__missing_keys = set(['exporter']) - data.keys()
        if data__missing_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must contain " + str(sorted(data__missing_keys)) + " properties")
        data_keys = set(data.keys())
        if "exporter" in data_keys:
            data_keys.remove("exporter")
            data__exporter = data["exporter"]
            validate____defs_pullmetricexporter(data__exporter, custom_formats, (name_prefix or "data") + ".exporter")
        if "producers" in data_keys:
            data_keys.remove("producers")
            data__producers = data["producers"]
            if not isinstance(data__producers, (list, tuple)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".producers must be array")
            data__producers_is_list = isinstance(data__producers, (list, tuple))
            if data__producers_is_list:
                data__producers_len = len(data__producers)
                if data__producers_len < 1:
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".producers must contain at least 1 items")
                for data__producers_x, data__producers_item in enumerate(data__producers):
                    validate____defs_metricproducer(data__producers_item, custom_formats, (name_prefix or "data") + ".producers[{data__producers_x}]".format(**locals()))
        if "cardinality_limits" in data_keys:
            data_keys.remove("cardinality_limits")
            data__cardinalitylimits = data["cardinality_limits"]
            validate____defs_cardinalitylimits(data__cardinalitylimits, custom_formats, (name_prefix or "data") + ".cardinality_limits")
        if data_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must not contain "+str(data_keys)+" properties")
    return data

def validate____defs_cardinalitylimits(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data_keys = set(data.keys())
        if "default" in data_keys:
            data_keys.remove("default")
            data__default = data["default"]
            if not isinstance(data__default, (int, NoneType)) and not (isinstance(data__default, float) and data__default.is_integer()) or isinstance(data__default, bool):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".default must be integer or null")
            if isinstance(data__default, (int, float, Decimal)):
                if data__default <= 0:
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".default must be bigger than 0")
        if "counter" in data_keys:
            data_keys.remove("counter")
            data__counter = data["counter"]
            if not isinstance(data__counter, (int, NoneType)) and not (isinstance(data__counter, float) and data__counter.is_integer()) or isinstance(data__counter, bool):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".counter must be integer or null")
            if isinstance(data__counter, (int, float, Decimal)):
                if data__counter <= 0:
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".counter must be bigger than 0")
        if "gauge" in data_keys:
            data_keys.remove("gauge")
            data__gauge = data["gauge"]
            if not isinstance(data__gauge, (int, NoneType)) and not (isinstance(data__gauge, float) and data__gauge.is_integer()) or isinstance(data__gauge, bool):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".gauge must be integer or null")
            if isinstance(data__gauge, (int, float, Decimal)):
                if data__gauge <= 0:
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".gauge must be bigger than 0")
        if "histogram" in data_keys:
            data_keys.remove("histogram")
            data__histogram = data["histogram"]
            if not isinstance(data__histogram, (int, NoneType)) and not (isinstance(data__histogram, float) and data__histogram.is_integer()) or isinstance(data__histogram, bool):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".histogram must be integer or null")
            if isinstance(data__histogram, (int, float, Decimal)):
                if data__histogram <= 0:
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".histogram must be bigger than 0")
        if "observable_counter" in data_keys:
            data_keys.remove("observable_counter")
            data__observablecounter = data["observable_counter"]
            if not isinstance(data__observablecounter, (int, NoneType)) and not (isinstance(data__observablecounter, float) and data__observablecounter.is_integer()) or isinstance(data__observablecounter, bool):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".observable_counter must be integer or null")
            if isinstance(data__observablecounter, (int, float, Decimal)):
                if data__observablecounter <= 0:
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".observable_counter must be bigger than 0")
        if "observable_gauge" in data_keys:
            data_keys.remove("observable_gauge")
            data__observablegauge = data["observable_gauge"]
            if not isinstance(data__observablegauge, (int, NoneType)) and not (isinstance(data__observablegauge, float) and data__observablegauge.is_integer()) or isinstance(data__observablegauge, bool):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".observable_gauge must be integer or null")
            if isinstance(data__observablegauge, (int, float, Decimal)):
                if data__observablegauge <= 0:
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".observable_gauge must be bigger than 0")
        if "observable_up_down_counter" in data_keys:
            data_keys.remove("observable_up_down_counter")
            data__observableupdowncounter = data["observable_up_down_counter"]
            if not isinstance(data__observableupdowncounter, (int, NoneType)) and not (isinstance(data__observableupdowncounter, float) and data__observableupdowncounter.is_integer()) or isinstance(data__observableupdowncounter, bool):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".observable_up_down_counter must be integer or null")
            if isinstance(data__observableupdowncounter, (int, float, Decimal)):
                if data__observableupdowncounter <= 0:
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".observable_up_down_counter must be bigger than 0")
        if "up_down_counter" in data_keys:
            data_keys.remove("up_down_counter")
            data__updowncounter = data["up_down_counter"]
            if not isinstance(data__updowncounter, (int, NoneType)) and not (isinstance(data__updowncounter, float) and data__updowncounter.is_integer()) or isinstance(data__updowncounter, bool):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".up_down_counter must be integer or null")
            if isinstance(data__updowncounter, (int, float, Decimal)):
                if data__updowncounter <= 0:
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".up_down_counter must be bigger than 0")
        if data_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must not contain "+str(data_keys)+" properties")
    return data

def validate____defs_metricproducer(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data_len = len(data)
        if data_len < 1:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must contain at least 1 properties")
        if data_len > 1:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must contain less than or equal to 1 properties")
        data_keys = set(data.keys())
        if "opencensus" in data_keys:
            data_keys.remove("opencensus")
            data__opencensus = data["opencensus"]
            validate____defs_opencensusmetricproducer(data__opencensus, custom_formats, (name_prefix or "data") + ".opencensus")
        for data_key in data_keys:
            if data_key not in ['opencensus']:
                data_value = data.get(data_key)
                if not isinstance(data_value, (dict, NoneType)):
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".{data_key}".format(**locals()) + " must be object or null")
    return data

def validate____defs_opencensusmetricproducer(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict, NoneType)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object or null")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data_keys = set(data.keys())
        if data_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must not contain "+str(data_keys)+" properties")
    return data

def validate____defs_pullmetricexporter(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data_len = len(data)
        if data_len < 1:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must contain at least 1 properties")
        if data_len > 1:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must contain less than or equal to 1 properties")
        data_keys = set(data.keys())
        if "prometheus/development" in data_keys:
            data_keys.remove("prometheus/development")
            data__prometheusdevelopment = data["prometheus/development"]
            validate____defs_experimentalprometheusmetricexporter(data__prometheusdevelopment, custom_formats, (name_prefix or "data") + ".prometheus/development")
        for data_key in data_keys:
            if data_key not in ['prometheus/development']:
                data_value = data.get(data_key)
                if not isinstance(data_value, (dict, NoneType)):
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".{data_key}".format(**locals()) + " must be object or null")
    return data

def validate____defs_experimentalprometheusmetricexporter(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict, NoneType)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object or null")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data_keys = set(data.keys())
        if "host" in data_keys:
            data_keys.remove("host")
            data__host = data["host"]
            if not isinstance(data__host, (str, NoneType)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".host must be string or null")
        if "port" in data_keys:
            data_keys.remove("port")
            data__port = data["port"]
            if not isinstance(data__port, (int, NoneType)) and not (isinstance(data__port, float) and data__port.is_integer()) or isinstance(data__port, bool):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".port must be integer or null")
        if "scope_info_enabled" in data_keys:
            data_keys.remove("scope_info_enabled")
            data__scopeinfoenabled = data["scope_info_enabled"]
            if not isinstance(data__scopeinfoenabled, (bool, NoneType)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".scope_info_enabled must be boolean or null")
        if "target_info_enabled/development" in data_keys:
            data_keys.remove("target_info_enabled/development")
            data__targetinfoenableddevelopment = data["target_info_enabled/development"]
            if not isinstance(data__targetinfoenableddevelopment, (bool, NoneType)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".target_info_enabled/development must be boolean or null")
        if "resource_constant_labels" in data_keys:
            data_keys.remove("resource_constant_labels")
            data__resourceconstantlabels = data["resource_constant_labels"]
            validate____defs_includeexclude(data__resourceconstantlabels, custom_formats, (name_prefix or "data") + ".resource_constant_labels")
        if "translation_strategy" in data_keys:
            data_keys.remove("translation_strategy")
            data__translationstrategy = data["translation_strategy"]
            validate____defs_experimentalprometheustranslationstrategy(data__translationstrategy, custom_formats, (name_prefix or "data") + ".translation_strategy")
        if data_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must not contain "+str(data_keys)+" properties")
    return data

def validate____defs_experimentalprometheustranslationstrategy(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (str, NoneType)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be string or null")
    if not (isinstance(data, str) and data == 'underscore_escaping_with_suffixes' or isinstance(data, str) and data == 'underscore_escaping_without_suffixes/development' or isinstance(data, str) and data == 'no_utf8_escaping_with_suffixes/development' or isinstance(data, str) and data == 'no_translation/development'):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be one of ['underscore_escaping_with_suffixes', 'underscore_escaping_without_suffixes/development', 'no_utf8_escaping_with_suffixes/development', 'no_translation/development']")
    return data

def validate____defs_periodicmetricreader(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data__missing_keys = set(['exporter']) - data.keys()
        if data__missing_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must contain " + str(sorted(data__missing_keys)) + " properties")
        data_keys = set(data.keys())
        if "interval" in data_keys:
            data_keys.remove("interval")
            data__interval = data["interval"]
            if not isinstance(data__interval, (int, NoneType)) and not (isinstance(data__interval, float) and data__interval.is_integer()) or isinstance(data__interval, bool):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".interval must be integer or null")
            if isinstance(data__interval, (int, float, Decimal)):
                if data__interval < 0:
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".interval must be bigger than or equal to 0")
        if "timeout" in data_keys:
            data_keys.remove("timeout")
            data__timeout = data["timeout"]
            if not isinstance(data__timeout, (int, NoneType)) and not (isinstance(data__timeout, float) and data__timeout.is_integer()) or isinstance(data__timeout, bool):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".timeout must be integer or null")
            if isinstance(data__timeout, (int, float, Decimal)):
                if data__timeout < 0:
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".timeout must be bigger than or equal to 0")
        if "max_export_batch_size/development" in data_keys:
            data_keys.remove("max_export_batch_size/development")
            data__maxexportbatchsizedevelopment = data["max_export_batch_size/development"]
            if not isinstance(data__maxexportbatchsizedevelopment, (int, NoneType)) and not (isinstance(data__maxexportbatchsizedevelopment, float) and data__maxexportbatchsizedevelopment.is_integer()) or isinstance(data__maxexportbatchsizedevelopment, bool):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".max_export_batch_size/development must be integer or null")
            if isinstance(data__maxexportbatchsizedevelopment, (int, float, Decimal)):
                if data__maxexportbatchsizedevelopment < 1:
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".max_export_batch_size/development must be bigger than or equal to 1")
        if "exporter" in data_keys:
            data_keys.remove("exporter")
            data__exporter = data["exporter"]
            validate____defs_pushmetricexporter(data__exporter, custom_formats, (name_prefix or "data") + ".exporter")
        if "producers" in data_keys:
            data_keys.remove("producers")
            data__producers = data["producers"]
            if not isinstance(data__producers, (list, tuple)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".producers must be array")
            data__producers_is_list = isinstance(data__producers, (list, tuple))
            if data__producers_is_list:
                data__producers_len = len(data__producers)
                if data__producers_len < 1:
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".producers must contain at least 1 items")
                for data__producers_x, data__producers_item in enumerate(data__producers):
                    validate____defs_metricproducer(data__producers_item, custom_formats, (name_prefix or "data") + ".producers[{data__producers_x}]".format(**locals()))
        if "cardinality_limits" in data_keys:
            data_keys.remove("cardinality_limits")
            data__cardinalitylimits = data["cardinality_limits"]
            validate____defs_cardinalitylimits(data__cardinalitylimits, custom_formats, (name_prefix or "data") + ".cardinality_limits")
        if data_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must not contain "+str(data_keys)+" properties")
    return data

def validate____defs_pushmetricexporter(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data_len = len(data)
        if data_len < 1:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must contain at least 1 properties")
        if data_len > 1:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must contain less than or equal to 1 properties")
        data_keys = set(data.keys())
        if "otlp_http" in data_keys:
            data_keys.remove("otlp_http")
            data__otlphttp = data["otlp_http"]
            validate____defs_otlphttpmetricexporter(data__otlphttp, custom_formats, (name_prefix or "data") + ".otlp_http")
        if "otlp_grpc" in data_keys:
            data_keys.remove("otlp_grpc")
            data__otlpgrpc = data["otlp_grpc"]
            validate____defs_otlpgrpcmetricexporter(data__otlpgrpc, custom_formats, (name_prefix or "data") + ".otlp_grpc")
        if "otlp_file/development" in data_keys:
            data_keys.remove("otlp_file/development")
            data__otlpfiledevelopment = data["otlp_file/development"]
            validate____defs_experimentalotlpfilemetricexporter(data__otlpfiledevelopment, custom_formats, (name_prefix or "data") + ".otlp_file/development")
        if "console" in data_keys:
            data_keys.remove("console")
            data__console = data["console"]
            validate____defs_consolemetricexporter(data__console, custom_formats, (name_prefix or "data") + ".console")
        for data_key in data_keys:
            if data_key not in ['otlp_http', 'otlp_grpc', 'otlp_file/development', 'console']:
                data_value = data.get(data_key)
                if not isinstance(data_value, (dict, NoneType)):
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".{data_key}".format(**locals()) + " must be object or null")
    return data

def validate____defs_consolemetricexporter(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict, NoneType)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object or null")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data_keys = set(data.keys())
        if "temporality_preference" in data_keys:
            data_keys.remove("temporality_preference")
            data__temporalitypreference = data["temporality_preference"]
            validate____defs_exportertemporalitypreference(data__temporalitypreference, custom_formats, (name_prefix or "data") + ".temporality_preference")
        if "default_histogram_aggregation" in data_keys:
            data_keys.remove("default_histogram_aggregation")
            data__defaulthistogramaggregation = data["default_histogram_aggregation"]
            validate____defs_exporterdefaulthistogramaggregation(data__defaulthistogramaggregation, custom_formats, (name_prefix or "data") + ".default_histogram_aggregation")
        if data_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must not contain "+str(data_keys)+" properties")
    return data

def validate____defs_exporterdefaulthistogramaggregation(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (str, NoneType)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be string or null")
    if not (isinstance(data, str) and data == 'explicit_bucket_histogram' or isinstance(data, str) and data == 'base2_exponential_bucket_histogram'):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be one of ['explicit_bucket_histogram', 'base2_exponential_bucket_histogram']")
    return data

def validate____defs_exportertemporalitypreference(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (str, NoneType)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be string or null")
    if not (isinstance(data, str) and data == 'cumulative' or isinstance(data, str) and data == 'delta' or isinstance(data, str) and data == 'low_memory'):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be one of ['cumulative', 'delta', 'low_memory']")
    return data

def validate____defs_experimentalotlpfilemetricexporter(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict, NoneType)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object or null")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data_keys = set(data.keys())
        if "output_stream" in data_keys:
            data_keys.remove("output_stream")
            data__outputstream = data["output_stream"]
            if not isinstance(data__outputstream, (str, NoneType)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".output_stream must be string or null")
        if "temporality_preference" in data_keys:
            data_keys.remove("temporality_preference")
            data__temporalitypreference = data["temporality_preference"]
            validate____defs_exportertemporalitypreference(data__temporalitypreference, custom_formats, (name_prefix or "data") + ".temporality_preference")
        if "default_histogram_aggregation" in data_keys:
            data_keys.remove("default_histogram_aggregation")
            data__defaulthistogramaggregation = data["default_histogram_aggregation"]
            validate____defs_exporterdefaulthistogramaggregation(data__defaulthistogramaggregation, custom_formats, (name_prefix or "data") + ".default_histogram_aggregation")
        if data_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must not contain "+str(data_keys)+" properties")
    return data

def validate____defs_otlpgrpcmetricexporter(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict, NoneType)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object or null")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data_keys = set(data.keys())
        if "endpoint" in data_keys:
            data_keys.remove("endpoint")
            data__endpoint = data["endpoint"]
            if not isinstance(data__endpoint, (str, NoneType)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".endpoint must be string or null")
        if "tls" in data_keys:
            data_keys.remove("tls")
            data__tls = data["tls"]
            validate____defs_grpctls(data__tls, custom_formats, (name_prefix or "data") + ".tls")
        if "headers" in data_keys:
            data_keys.remove("headers")
            data__headers = data["headers"]
            if not isinstance(data__headers, (list, tuple)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".headers must be array")
            data__headers_is_list = isinstance(data__headers, (list, tuple))
            if data__headers_is_list:
                data__headers_len = len(data__headers)
                if data__headers_len < 1:
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".headers must contain at least 1 items")
                for data__headers_x, data__headers_item in enumerate(data__headers):
                    validate____defs_namestringvaluepair(data__headers_item, custom_formats, (name_prefix or "data") + ".headers[{data__headers_x}]".format(**locals()))
        if "headers_list" in data_keys:
            data_keys.remove("headers_list")
            data__headerslist = data["headers_list"]
            if not isinstance(data__headerslist, (str, NoneType)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".headers_list must be string or null")
        if "compression" in data_keys:
            data_keys.remove("compression")
            data__compression = data["compression"]
            if not isinstance(data__compression, (str, NoneType)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".compression must be string or null")
        if "timeout" in data_keys:
            data_keys.remove("timeout")
            data__timeout = data["timeout"]
            if not isinstance(data__timeout, (int, NoneType)) and not (isinstance(data__timeout, float) and data__timeout.is_integer()) or isinstance(data__timeout, bool):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".timeout must be integer or null")
            if isinstance(data__timeout, (int, float, Decimal)):
                if data__timeout < 0:
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".timeout must be bigger than or equal to 0")
        if "temporality_preference" in data_keys:
            data_keys.remove("temporality_preference")
            data__temporalitypreference = data["temporality_preference"]
            validate____defs_exportertemporalitypreference(data__temporalitypreference, custom_formats, (name_prefix or "data") + ".temporality_preference")
        if "default_histogram_aggregation" in data_keys:
            data_keys.remove("default_histogram_aggregation")
            data__defaulthistogramaggregation = data["default_histogram_aggregation"]
            validate____defs_exporterdefaulthistogramaggregation(data__defaulthistogramaggregation, custom_formats, (name_prefix or "data") + ".default_histogram_aggregation")
        if data_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must not contain "+str(data_keys)+" properties")
    return data

def validate____defs_otlphttpmetricexporter(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict, NoneType)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object or null")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data_keys = set(data.keys())
        if "endpoint" in data_keys:
            data_keys.remove("endpoint")
            data__endpoint = data["endpoint"]
            if not isinstance(data__endpoint, (str, NoneType)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".endpoint must be string or null")
        if "tls" in data_keys:
            data_keys.remove("tls")
            data__tls = data["tls"]
            validate____defs_httptls(data__tls, custom_formats, (name_prefix or "data") + ".tls")
        if "headers" in data_keys:
            data_keys.remove("headers")
            data__headers = data["headers"]
            if not isinstance(data__headers, (list, tuple)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".headers must be array")
            data__headers_is_list = isinstance(data__headers, (list, tuple))
            if data__headers_is_list:
                data__headers_len = len(data__headers)
                if data__headers_len < 1:
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".headers must contain at least 1 items")
                for data__headers_x, data__headers_item in enumerate(data__headers):
                    validate____defs_namestringvaluepair(data__headers_item, custom_formats, (name_prefix or "data") + ".headers[{data__headers_x}]".format(**locals()))
        if "headers_list" in data_keys:
            data_keys.remove("headers_list")
            data__headerslist = data["headers_list"]
            if not isinstance(data__headerslist, (str, NoneType)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".headers_list must be string or null")
        if "compression" in data_keys:
            data_keys.remove("compression")
            data__compression = data["compression"]
            if not isinstance(data__compression, (str, NoneType)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".compression must be string or null")
        if "timeout" in data_keys:
            data_keys.remove("timeout")
            data__timeout = data["timeout"]
            if not isinstance(data__timeout, (int, NoneType)) and not (isinstance(data__timeout, float) and data__timeout.is_integer()) or isinstance(data__timeout, bool):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".timeout must be integer or null")
            if isinstance(data__timeout, (int, float, Decimal)):
                if data__timeout < 0:
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".timeout must be bigger than or equal to 0")
        if "encoding" in data_keys:
            data_keys.remove("encoding")
            data__encoding = data["encoding"]
            validate____defs_otlphttpencoding(data__encoding, custom_formats, (name_prefix or "data") + ".encoding")
        if "temporality_preference" in data_keys:
            data_keys.remove("temporality_preference")
            data__temporalitypreference = data["temporality_preference"]
            validate____defs_exportertemporalitypreference(data__temporalitypreference, custom_formats, (name_prefix or "data") + ".temporality_preference")
        if "default_histogram_aggregation" in data_keys:
            data_keys.remove("default_histogram_aggregation")
            data__defaulthistogramaggregation = data["default_histogram_aggregation"]
            validate____defs_exporterdefaulthistogramaggregation(data__defaulthistogramaggregation, custom_formats, (name_prefix or "data") + ".default_histogram_aggregation")
        if data_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must not contain "+str(data_keys)+" properties")
    return data

def validate____defs_loggerprovider(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data__missing_keys = set(['processors']) - data.keys()
        if data__missing_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must contain " + str(sorted(data__missing_keys)) + " properties")
        data_keys = set(data.keys())
        if "processors" in data_keys:
            data_keys.remove("processors")
            data__processors = data["processors"]
            if not isinstance(data__processors, (list, tuple)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".processors must be array")
            data__processors_is_list = isinstance(data__processors, (list, tuple))
            if data__processors_is_list:
                data__processors_len = len(data__processors)
                if data__processors_len < 1:
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".processors must contain at least 1 items")
                for data__processors_x, data__processors_item in enumerate(data__processors):
                    validate____defs_logrecordprocessor(data__processors_item, custom_formats, (name_prefix or "data") + ".processors[{data__processors_x}]".format(**locals()))
        if "limits" in data_keys:
            data_keys.remove("limits")
            data__limits = data["limits"]
            validate____defs_logrecordlimits(data__limits, custom_formats, (name_prefix or "data") + ".limits")
        if "logger_configurator/development" in data_keys:
            data_keys.remove("logger_configurator/development")
            data__loggerconfiguratordevelopment = data["logger_configurator/development"]
            validate____defs_experimentalloggerconfigurator(data__loggerconfiguratordevelopment, custom_formats, (name_prefix or "data") + ".logger_configurator/development")
        if data_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must not contain "+str(data_keys)+" properties")
    return data

def validate____defs_experimentalloggerconfigurator(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data_keys = set(data.keys())
        if "default_config" in data_keys:
            data_keys.remove("default_config")
            data__defaultconfig = data["default_config"]
            validate____defs_experimentalloggerconfig(data__defaultconfig, custom_formats, (name_prefix or "data") + ".default_config")
        if "loggers" in data_keys:
            data_keys.remove("loggers")
            data__loggers = data["loggers"]
            if not isinstance(data__loggers, (list, tuple)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".loggers must be array")
            data__loggers_is_list = isinstance(data__loggers, (list, tuple))
            if data__loggers_is_list:
                data__loggers_len = len(data__loggers)
                if data__loggers_len < 1:
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".loggers must contain at least 1 items")
                for data__loggers_x, data__loggers_item in enumerate(data__loggers):
                    validate____defs_experimentalloggermatcherandconfig(data__loggers_item, custom_formats, (name_prefix or "data") + ".loggers[{data__loggers_x}]".format(**locals()))
        if data_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must not contain "+str(data_keys)+" properties")
    return data

def validate____defs_experimentalloggermatcherandconfig(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data__missing_keys = set(['name', 'config']) - data.keys()
        if data__missing_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must contain " + str(sorted(data__missing_keys)) + " properties")
        data_keys = set(data.keys())
        if "name" in data_keys:
            data_keys.remove("name")
            data__name = data["name"]
            if not isinstance(data__name, (str)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".name must be string")
        if "config" in data_keys:
            data_keys.remove("config")
            data__config = data["config"]
            validate____defs_experimentalloggerconfig(data__config, custom_formats, (name_prefix or "data") + ".config")
        if data_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must not contain "+str(data_keys)+" properties")
    return data

def validate____defs_experimentalloggerconfig(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data_keys = set(data.keys())
        if "enabled" in data_keys:
            data_keys.remove("enabled")
            data__enabled = data["enabled"]
            if not isinstance(data__enabled, (bool, NoneType)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".enabled must be boolean or null")
        if "minimum_severity" in data_keys:
            data_keys.remove("minimum_severity")
            data__minimumseverity = data["minimum_severity"]
            validate____defs_severitynumber(data__minimumseverity, custom_formats, (name_prefix or "data") + ".minimum_severity")
        if "trace_based" in data_keys:
            data_keys.remove("trace_based")
            data__tracebased = data["trace_based"]
            if not isinstance(data__tracebased, (bool, NoneType)):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".trace_based must be boolean or null")
        if data_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must not contain "+str(data_keys)+" properties")
    return data

def validate____defs_logrecordlimits(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data_keys = set(data.keys())
        if "attribute_value_length_limit" in data_keys:
            data_keys.remove("attribute_value_length_limit")
            data__attributevaluelengthlimit = data["attribute_value_length_limit"]
            if not isinstance(data__attributevaluelengthlimit, (int, NoneType)) and not (isinstance(data__attributevaluelengthlimit, float) and data__attributevaluelengthlimit.is_integer()) or isinstance(data__attributevaluelengthlimit, bool):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".attribute_value_length_limit must be integer or null")
            if isinstance(data__attributevaluelengthlimit, (int, float, Decimal)):
                if data__attributevaluelengthlimit < 0:
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".attribute_value_length_limit must be bigger than or equal to 0")
        if "attribute_count_limit" in data_keys:
            data_keys.remove("attribute_count_limit")
            data__attributecountlimit = data["attribute_count_limit"]
            if not isinstance(data__attributecountlimit, (int, NoneType)) and not (isinstance(data__attributecountlimit, float) and data__attributecountlimit.is_integer()) or isinstance(data__attributecountlimit, bool):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".attribute_count_limit must be integer or null")
            if isinstance(data__attributecountlimit, (int, float, Decimal)):
                if data__attributecountlimit < 0:
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".attribute_count_limit must be bigger than or equal to 0")
        if data_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must not contain "+str(data_keys)+" properties")
    return data

def validate____defs_logrecordprocessor(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data_len = len(data)
        if data_len < 1:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must contain at least 1 properties")
        if data_len > 1:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must contain less than or equal to 1 properties")
        data_keys = set(data.keys())
        if "batch" in data_keys:
            data_keys.remove("batch")
            data__batch = data["batch"]
            validate____defs_batchlogrecordprocessor(data__batch, custom_formats, (name_prefix or "data") + ".batch")
        if "simple" in data_keys:
            data_keys.remove("simple")
            data__simple = data["simple"]
            validate____defs_simplelogrecordprocessor(data__simple, custom_formats, (name_prefix or "data") + ".simple")
        if "event_to_span_event_bridge/development" in data_keys:
            data_keys.remove("event_to_span_event_bridge/development")
            data__eventtospaneventbridgedevelopment = data["event_to_span_event_bridge/development"]
            validate____defs_experimentaleventtospaneventbridgelogrecordprocessor(data__eventtospaneventbridgedevelopment, custom_formats, (name_prefix or "data") + ".event_to_span_event_bridge/development")
        for data_key in data_keys:
            if data_key not in ['batch', 'simple', 'event_to_span_event_bridge/development']:
                data_value = data.get(data_key)
                if not isinstance(data_value, (dict, NoneType)):
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".{data_key}".format(**locals()) + " must be object or null")
    return data

def validate____defs_experimentaleventtospaneventbridgelogrecordprocessor(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict, NoneType)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object or null")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data_keys = set(data.keys())
        if data_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must not contain "+str(data_keys)+" properties")
    return data

def validate____defs_simplelogrecordprocessor(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data__missing_keys = set(['exporter']) - data.keys()
        if data__missing_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must contain " + str(sorted(data__missing_keys)) + " properties")
        data_keys = set(data.keys())
        if "exporter" in data_keys:
            data_keys.remove("exporter")
            data__exporter = data["exporter"]
            validate____defs_logrecordexporter(data__exporter, custom_formats, (name_prefix or "data") + ".exporter")
        if data_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must not contain "+str(data_keys)+" properties")
    return data

def validate____defs_logrecordexporter(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data_len = len(data)
        if data_len < 1:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must contain at least 1 properties")
        if data_len > 1:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must contain less than or equal to 1 properties")
        data_keys = set(data.keys())
        if "otlp_http" in data_keys:
            data_keys.remove("otlp_http")
            data__otlphttp = data["otlp_http"]
            validate____defs_otlphttpexporter(data__otlphttp, custom_formats, (name_prefix or "data") + ".otlp_http")
        if "otlp_grpc" in data_keys:
            data_keys.remove("otlp_grpc")
            data__otlpgrpc = data["otlp_grpc"]
            validate____defs_otlpgrpcexporter(data__otlpgrpc, custom_formats, (name_prefix or "data") + ".otlp_grpc")
        if "otlp_file/development" in data_keys:
            data_keys.remove("otlp_file/development")
            data__otlpfiledevelopment = data["otlp_file/development"]
            validate____defs_experimentalotlpfileexporter(data__otlpfiledevelopment, custom_formats, (name_prefix or "data") + ".otlp_file/development")
        if "console" in data_keys:
            data_keys.remove("console")
            data__console = data["console"]
            validate____defs_consoleexporter(data__console, custom_formats, (name_prefix or "data") + ".console")
        for data_key in data_keys:
            if data_key not in ['otlp_http', 'otlp_grpc', 'otlp_file/development', 'console']:
                data_value = data.get(data_key)
                if not isinstance(data_value, (dict, NoneType)):
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".{data_key}".format(**locals()) + " must be object or null")
    return data

def validate____defs_batchlogrecordprocessor(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data__missing_keys = set(['exporter']) - data.keys()
        if data__missing_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must contain " + str(sorted(data__missing_keys)) + " properties")
        data_keys = set(data.keys())
        if "schedule_delay" in data_keys:
            data_keys.remove("schedule_delay")
            data__scheduledelay = data["schedule_delay"]
            if not isinstance(data__scheduledelay, (int, NoneType)) and not (isinstance(data__scheduledelay, float) and data__scheduledelay.is_integer()) or isinstance(data__scheduledelay, bool):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".schedule_delay must be integer or null")
            if isinstance(data__scheduledelay, (int, float, Decimal)):
                if data__scheduledelay < 0:
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".schedule_delay must be bigger than or equal to 0")
        if "export_timeout" in data_keys:
            data_keys.remove("export_timeout")
            data__exporttimeout = data["export_timeout"]
            if not isinstance(data__exporttimeout, (int, NoneType)) and not (isinstance(data__exporttimeout, float) and data__exporttimeout.is_integer()) or isinstance(data__exporttimeout, bool):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".export_timeout must be integer or null")
            if isinstance(data__exporttimeout, (int, float, Decimal)):
                if data__exporttimeout < 0:
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".export_timeout must be bigger than or equal to 0")
        if "max_queue_size" in data_keys:
            data_keys.remove("max_queue_size")
            data__maxqueuesize = data["max_queue_size"]
            if not isinstance(data__maxqueuesize, (int, NoneType)) and not (isinstance(data__maxqueuesize, float) and data__maxqueuesize.is_integer()) or isinstance(data__maxqueuesize, bool):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".max_queue_size must be integer or null")
            if isinstance(data__maxqueuesize, (int, float, Decimal)):
                if data__maxqueuesize <= 0:
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".max_queue_size must be bigger than 0")
        if "max_export_batch_size" in data_keys:
            data_keys.remove("max_export_batch_size")
            data__maxexportbatchsize = data["max_export_batch_size"]
            if not isinstance(data__maxexportbatchsize, (int, NoneType)) and not (isinstance(data__maxexportbatchsize, float) and data__maxexportbatchsize.is_integer()) or isinstance(data__maxexportbatchsize, bool):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".max_export_batch_size must be integer or null")
            if isinstance(data__maxexportbatchsize, (int, float, Decimal)):
                if data__maxexportbatchsize <= 0:
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".max_export_batch_size must be bigger than 0")
        if "exporter" in data_keys:
            data_keys.remove("exporter")
            data__exporter = data["exporter"]
            validate____defs_logrecordexporter(data__exporter, custom_formats, (name_prefix or "data") + ".exporter")
        if data_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must not contain "+str(data_keys)+" properties")
    return data

def validate____defs_attributelimits(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (dict)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be object")
    data_is_dict = isinstance(data, dict)
    if data_is_dict:
        data_keys = set(data.keys())
        if "attribute_value_length_limit" in data_keys:
            data_keys.remove("attribute_value_length_limit")
            data__attributevaluelengthlimit = data["attribute_value_length_limit"]
            if not isinstance(data__attributevaluelengthlimit, (int, NoneType)) and not (isinstance(data__attributevaluelengthlimit, float) and data__attributevaluelengthlimit.is_integer()) or isinstance(data__attributevaluelengthlimit, bool):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".attribute_value_length_limit must be integer or null")
            if isinstance(data__attributevaluelengthlimit, (int, float, Decimal)):
                if data__attributevaluelengthlimit < 0:
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".attribute_value_length_limit must be bigger than or equal to 0")
        if "attribute_count_limit" in data_keys:
            data_keys.remove("attribute_count_limit")
            data__attributecountlimit = data["attribute_count_limit"]
            if not isinstance(data__attributecountlimit, (int, NoneType)) and not (isinstance(data__attributecountlimit, float) and data__attributecountlimit.is_integer()) or isinstance(data__attributecountlimit, bool):
                raise JsonSchemaValueException("" + (name_prefix or "data") + ".attribute_count_limit must be integer or null")
            if isinstance(data__attributecountlimit, (int, float, Decimal)):
                if data__attributecountlimit < 0:
                    raise JsonSchemaValueException("" + (name_prefix or "data") + ".attribute_count_limit must be bigger than or equal to 0")
        if data_keys:
            raise JsonSchemaValueException("" + (name_prefix or "data") + " must not contain "+str(data_keys)+" properties")
    return data

def validate____defs_severitynumber(data, custom_formats={}, name_prefix=None):
    if not isinstance(data, (str, NoneType)):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be string or null")
    if not (isinstance(data, str) and data == 'trace' or isinstance(data, str) and data == 'trace2' or isinstance(data, str) and data == 'trace3' or isinstance(data, str) and data == 'trace4' or isinstance(data, str) and data == 'debug' or isinstance(data, str) and data == 'debug2' or isinstance(data, str) and data == 'debug3' or isinstance(data, str) and data == 'debug4' or isinstance(data, str) and data == 'info' or isinstance(data, str) and data == 'info2' or isinstance(data, str) and data == 'info3' or isinstance(data, str) and data == 'info4' or isinstance(data, str) and data == 'warn' or isinstance(data, str) and data == 'warn2' or isinstance(data, str) and data == 'warn3' or isinstance(data, str) and data == 'warn4' or isinstance(data, str) and data == 'error' or isinstance(data, str) and data == 'error2' or isinstance(data, str) and data == 'error3' or isinstance(data, str) and data == 'error4' or isinstance(data, str) and data == 'fatal' or isinstance(data, str) and data == 'fatal2' or isinstance(data, str) and data == 'fatal3' or isinstance(data, str) and data == 'fatal4'):
        raise JsonSchemaValueException("" + (name_prefix or "data") + " must be one of ['trace', 'trace2', 'trace3', 'trace4', 'debug', 'debug2', 'debug3', 'debug4', 'info', 'info2', 'info3', 'info4', 'warn', 'warn2', 'warn3', 'warn4', 'error', 'error2', 'error3', 'error4', 'fatal', 'fatal2', 'fatal3', 'fatal4']")
    return data
