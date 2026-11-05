import tempfile
import unittest
from pathlib import Path
from evaluate_cadence import evaluate
from compare_preserved_64 import compare

class CadenceHelperTests(unittest.TestCase):
    def test_imports_are_safe_and_existing_outputs_are_protected(self):
        with tempfile.TemporaryDirectory() as temporary:
            output=Path(temporary)/'keep.json';output.write_text('keep')
            for function in [evaluate,compare]:
                with self.assertRaisesRegex(ValueError,'overwrite'):
                    function(Path(temporary)/'missing-input',output)
                self.assertEqual(output.read_text(),'keep')

if __name__=='__main__':unittest.main()
