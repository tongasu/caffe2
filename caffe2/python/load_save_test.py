from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
import errno
import hypothesis.strategies as st
from hypothesis import given
import numpy as np
import os
import shutil
import tempfile
import unittest

from caffe2.proto import caffe2_pb2
from caffe2.python import core, test_util, workspace

if workspace.has_gpu_support:
    DEVICES = [caffe2_pb2.CPU, caffe2_pb2.CUDA]
    max_gpuid = workspace.NumCudaDevices() - 1
else:
    DEVICES = [caffe2_pb2.CPU]
    max_gpuid = 0


# Utility class for other loading tests, don't add test functions here
# Inherit from this test instead. If you add a test here,
# each derived class will inherit it as well and cause test duplication
class TestLoadSaveBase(test_util.TestCase):

    def __init__(self, methodName, db_type='minidb'):
        super(TestLoadSaveBase, self).__init__(methodName)
        self._db_type = db_type

    @given(src_device_type=st.sampled_from(DEVICES),
           src_gpu_id=st.integers(min_value=0, max_value=max_gpuid),
           dst_device_type=st.sampled_from(DEVICES),
           dst_gpu_id=st.integers(min_value=0, max_value=max_gpuid))
    def load_save(self, src_device_type, src_gpu_id,
                  dst_device_type, dst_gpu_id):
        workspace.ResetWorkspace()
        dtypes = [np.float16, np.float32, np.float64, np.bool, np.int8,
                  np.int16, np.int32, np.int64, np.uint8, np.uint16]
        arrays = [np.random.permutation(6).reshape(2, 3).astype(T)
                  for T in dtypes]
        src_device_option = core.DeviceOption(
            src_device_type, src_gpu_id)
        dst_device_option = core.DeviceOption(
            dst_device_type, dst_gpu_id)

        for i, arr in enumerate(arrays):
            self.assertTrue(workspace.FeedBlob(str(i), arr, src_device_option))
            self.assertTrue(workspace.HasBlob(str(i)))

        try:
            # Saves the blobs to a local db.
            tmp_folder = tempfile.mkdtemp()
            op = core.CreateOperator(
                "Save",
                [str(i) for i in range(len(arrays))], [],
                absolute_path=1,
                db=os.path.join(tmp_folder, "db"), db_type=self._db_type)
            self.assertTrue(workspace.RunOperatorOnce(op))

            # Reset the workspace so that anything we load is surely loaded
            # from the serialized proto.
            workspace.ResetWorkspace()
            self.assertEqual(len(workspace.Blobs()), 0)

            def _LoadTest(keep_device, device_type, gpu_id, blobs, loadAll):
                """A helper subfunction to test keep and not keep."""
                op = core.CreateOperator(
                    "Load",
                    [], blobs,
                    absolute_path=1,
                    db=os.path.join(tmp_folder, "db"), db_type=self._db_type,
                    device_option=dst_device_option,
                    keep_device=keep_device,
                    load_all=loadAll)
                self.assertTrue(workspace.RunOperatorOnce(op))
                for i, arr in enumerate(arrays):
                    self.assertTrue(workspace.HasBlob(str(i)))
                    fetched = workspace.FetchBlob(str(i))
                    self.assertEqual(fetched.dtype, arr.dtype)
                    np.testing.assert_array_equal(
                        workspace.FetchBlob(str(i)), arr)
                    proto = caffe2_pb2.BlobProto()
                    proto.ParseFromString(workspace.SerializeBlob(str(i)))
                    self.assertTrue(proto.HasField('tensor'))
                    self.assertEqual(proto.tensor.device_detail.device_type,
                                     device_type)
                    if device_type == caffe2_pb2.CUDA:
                        self.assertEqual(proto.tensor.device_detail.cuda_gpu_id,
                                         gpu_id)

            blobs = [str(i) for i in range(len(arrays))]
            # Load using device option stored in the proto, i.e.
            # src_device_option
            _LoadTest(1, src_device_type, src_gpu_id, blobs, 0)
            # Load again, but this time load into dst_device_option.
            _LoadTest(0, dst_device_type, dst_gpu_id, blobs, 0)
            # Load back to the src_device_option to see if both paths are able
            # to reallocate memory.
            _LoadTest(1, src_device_type, src_gpu_id, blobs, 0)
            # Reset the workspace, and load directly into the dst_device_option.
            workspace.ResetWorkspace()
            _LoadTest(0, dst_device_type, dst_gpu_id, blobs, 0)

            # Test load all which loads all blobs in the db into the workspace.
            workspace.ResetWorkspace()
            _LoadTest(1, src_device_type, src_gpu_id, [], 1)
            # Load again making sure that overwrite functionality works.
            _LoadTest(1, src_device_type, src_gpu_id, [], 1)
            # Load again with different device.
            _LoadTest(0, dst_device_type, dst_gpu_id, [], 1)
            workspace.ResetWorkspace()
            _LoadTest(0, dst_device_type, dst_gpu_id, [], 1)
        finally:
            # clean up temp folder.
            try:
                shutil.rmtree(tmp_folder)
            except OSError as e:
                if e.errno != errno.ENOENT:
                    raise


class TestLoadSave(TestLoadSaveBase):

    def testLoadSave(self):
        self.load_save()

    def testRepeatedArgs(self):
        dtypes = [np.float16, np.float32, np.float64, np.bool, np.int8,
                  np.int16, np.int32, np.int64, np.uint8, np.uint16]
        arrays = [np.random.permutation(6).reshape(2, 3).astype(T)
                  for T in dtypes]

        for i, arr in enumerate(arrays):
            self.assertTrue(workspace.FeedBlob(str(i), arr))
            self.assertTrue(workspace.HasBlob(str(i)))

        # Saves the blobs to a local db.
        tmp_folder = tempfile.mkdtemp()
        op = core.CreateOperator(
            "Save",
            [str(i) for i in range(len(arrays))] * 2, [],
            absolute_path=1,
            db=os.path.join(tmp_folder, "db"), db_type=self._db_type)
        with self.assertRaises(RuntimeError):
            self.assertRaises(workspace.RunOperatorOnce(op))


if __name__ == '__main__':
    unittest.main()
