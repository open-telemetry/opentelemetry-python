# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0


class IterEntryPoint:
    def __init__(self, name, class_type):
        self.name = name
        self.class_type = class_type

    def load(self):
        return self.class_type
