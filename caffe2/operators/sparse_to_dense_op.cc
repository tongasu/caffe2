#include "sparse_to_dense_op.h"

#include "caffe2/core/context.h"

namespace caffe2 {

namespace {
REGISTER_CPU_OPERATOR(SparseToDense, SparseToDenseOp<CPUContext>);

OPERATOR_SCHEMA(SparseToDense)
    .NumInputs(2, 3)
    .NumOutputs(1)
    .SetDoc(R"DOC(
Convert sparse representations to dense with given indices.

Transforms a sparse representation of map<id, value> represented as `indices`
vector and `values` tensor into a compacted tensor where the first dimension
is determined by the first dimension of the 3rd input if it is given or the
max index. Missing values are filled with zeros. After running this op:

```
output[indices[i], :] = values[i] #
output[j, ...] = 0 if j not in indices
```
)DOC")
    .Input(0, "indices", "1-D int32/int64 tensor of concatenated ids of data")
    .Input(1, "values", "Data tensor, first dimension has to match `indices`")
    .Input(
        2,
        "data_to_infer_dim",
        "Optional: if provided, the first dimension of output is the first "
        "dimension of this tensor.")
    .Output(
        0,
        "output",
        "Output tensor of the same type as `values` of shape `[len(lengths), "
        "len(mask)] + shape(default_value)` (if `lengths` is not provided the "
        "first dimension is omitted)");

NO_GRADIENT(SparseToDense);
} // namespace
} // namespace caffe2
