import tempfile
import unittest
from pathlib import Path
from evaluate_control_selection import run as evaluate_control
from evaluate_patch_rejection import run as evaluate_patch

class EvaluationWrapperTests(unittest.TestCase):
    def test_existing_outputs_are_protected_before_any_input_read(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);output=root/'keep.json';output.write_text('keep')
            with self.assertRaisesRegex(ValueError,'existing'):
                evaluate_control(root/'missing',root/'missing',root,96)
            with self.assertRaisesRegex(ValueError,'overwrite'):
                evaluate_patch(root/'missing',root/'missing',root/'missing',output)
            self.assertEqual(output.read_text(),'keep')

if __name__=='__main__':unittest.main()
