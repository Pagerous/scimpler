::: scimpler.error.ValidationError
    options:
        show_category_heading: false

## Pre-defined error codes

| <div style="width:100px">Error code | <div style="width:200px"> Description                                                                 |
|:-----------------------------------:|-------------------------------------------------------------------------------------------------------|
|                **1**                | Value has correct type, but bad syntax (e.g. does not match regular expression).                      | 
|                **2**                | Value has bad type and can not be validated further.                                                  | 
|                **3**                | Value has bad encoding, e.g. for binary attributes, base64 encoding is required.                      |
|                **4**                | Value has correct type and syntax, but bad semantics.                                                 |
|                **5**                | Value is expected, but is missing.                                                                    |
|                **6**                | Value is provided when it should not be.                                                              |
|                **7**                | Value is returned when it should not be.                                                              |
|                **8**                | Value must be equal to specific value, but it is not.                                                 |
|                **9**                | Value must be one of specific values.                                                                 |
|               **10**                | Value contains duplicates.                                                                            |
|               **11**                | Value can not be provided if other value is provided.                                                 |
|               **12**                | The `schemas` attribute is missing base schema.                                                       |
|               **13**                | The `schemas` attribute is missing one of the extensions which attributes are present in the data.    |
|               **14**                | The `schemas` attribute contains unknown schema URI.                                                  |
|               **15**                | The `primary` sub-attribute set to `True` appears more than once in multi-valued complex attribute.   |
|               **16**                | The value of scim reference attribute is unknown.                                                     |
|               **17**                | The provided attribute name is invalid.                                                               |
|               **18**                | Bad value of error `status`.                                                                          |
|               **19**                | Bad value of returned status code.                                                                    |
|               **20**                | Bad number of resources returned from query endpoint.                                                 |
|               **21**                | The returned resource does not match the filter.                                                      |
|               **22**                | Resources are not sorted, according to the sorter.                                                    |
|               **25**                | Unknown bulk operation resource.                                                                      |
|               **26**                | Number of bulk operations exceeded the configured maximum.                                            |
|               **27**                | Number of errors in returned bulk operations exceeded provided maximum.                               |
|               **28**                | The `PATCH` operation path indicates non-existing attribute.                                          |
|               **29**                | The attribute specified in `PATCH` operation can not be modified.                                     |
|               **30**                | The attribute specified in `PATCH` operation can not be removed.                                      |
|               **31**                | The provided value is not supported.                                                                  |
|               **100**               | At least one of the round brackets in the filter expression is not opened / closed.                   |
|               **101**               | At least one of the complex attribute group brackets in the filter expression is not opened / closed. |
|               **102**               | Complex attribute group operator used for sub-attribute.                                              |
|               **103**               | The operator in the filter expression misses an operand.                                              |
|               **104**               | Unknown operator in the filter expression.                                                            |
|               **105**               | No inner expression in the round brackets.                                                            |
|               **106**               | Unknown expression, generic filter error if validation fails from other reasons.                      |
|               **107**               | Complex attribute group operator contains inner complex attribute group.                              |
|               **108**               | Complex attribute group operator contains no inner expression.                                        |
|               **109**               | Not recognized operand for the operator.                                                              |
|               **110**               | Operand's value not compatible with the specific operator.                                            |
