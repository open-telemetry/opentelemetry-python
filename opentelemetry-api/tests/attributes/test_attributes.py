    def test_invalid_anyvalue_type_raises_typeerror(self):
        class BadStr:
            def __str__(self):
                raise Exception("boom")

        with self.assertRaises(TypeError):
            _clean_extended_attribute_value(BadStr(), None)

    def test_deepcopy(self):
        bdict = BoundedAttributes(4, self.base, immutable=False)
        bdict.dropped = 10
        bdict_copy = copy.deepcopy(bdict)

        for key in bdict_copy:
            self.assertEqual(bdict_copy[key], bdict[key])

        self.assertEqual(bdict_copy.dropped, bdict.dropped)
        self.assertEqual(bdict_copy.maxlen, bdict.maxlen)
        self.assertEqual(bdict_copy.max_value_len, bdict.max_value_len)

        bdict_copy["name"] = "Bob"
        self.assertNotEqual(bdict_copy["name"], bdict["name"])

        bdict["age"] = 99
        self.assertNotEqual(bdict["age"], bdict_copy["age"])

    def test_deepcopy_preserves_immutability(self):
        bdict = BoundedAttributes(
            maxlen=4, attributes=self.base, immutable=True
        )
        bdict_copy = copy.deepcopy(bdict)

        with self.assertRaises(TypeError):
            bdict_copy["invalid"] = "invalid"