import unittest
from unittest.mock import Mock, patch


class DummyModel:
    def __init__(self):
        self.moved_to = None

    def to(self, device):
        self.moved_to = device
        return self


class TestBenchmarkLoader(unittest.TestCase):
    def test_load_model_and_tokenizer_disables_low_cpu_mem_usage(self):
        # Import inside test so our patches are applied to the module objects.
        import src.benchmark as bench

        dummy_model = DummyModel()
        dummy_tokenizer = Mock()
        dummy_tokenizer.pad_token = None
        dummy_tokenizer.eos_token = "</s>"

        with (
            patch.object(bench.torch.cuda, "is_available", return_value=False),
            patch.object(bench.torch.backends.mps, "is_available", return_value=False),
            patch.object(
                bench.AutoPeftModelForCausalLM,
                "from_pretrained",
                return_value=dummy_model,
            ) as fp,
            patch.object(
                bench.AutoTokenizer,
                "from_pretrained",
                return_value=dummy_tokenizer,
            ) as tp,
        ):
            _model, _tok = bench.load_model_and_tokenizer(bench.Path("/tmp/fake_model"))

        # Regression assertion: we must force-disable low-mem meta init to prevent
        # "Cannot copy out of meta tensor; no data!" when calling Module.to(...).
        self.assertEqual(fp.call_args.kwargs.get("low_cpu_mem_usage"), False)
        self.assertIsNone(fp.call_args.kwargs.get("device_map"))
        tp.assert_called_once()

    def test_preferred_device_ignores_mps(self):
        import src.benchmark as bench

        with (
            patch.object(bench.torch.cuda, "is_available", return_value=False),
            patch.object(bench.torch.backends.mps, "is_available", return_value=True),
        ):
            self.assertEqual(str(bench._preferred_device()), "cpu")


if __name__ == "__main__":
    unittest.main()


