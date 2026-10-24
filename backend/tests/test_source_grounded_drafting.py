import sys
import unittest
from types import SimpleNamespace, ModuleType
from unittest.mock import patch

sys.path.insert(0, "backend")
from app.ai import draft_procedure
from app.transcription import transcribe_video
from app.source_evidence import load_source_excerpts
from app.db import Base
from app.models import Source, KnowledgeChunk
from sqlalchemy import create_engine
from sqlalchemy.orm import Session


class DraftGroundingTests(unittest.TestCase):
    def setUp(self):
        self.excerpts = [{
            "text": "ドリルの電源を切り、チャックとドリルビットに損傷がないか確認します。ドリルの電源を切り、チャックとドリルビットに損傷がないか確認します。操作前に周囲を確認します。",
            "source_ref": "DrillMachine.mp4 · 00:12",
            "timestamp": "00:12",
            "source_id": 21,
        }]

    @patch("app.ai.ollama")
    def test_selected_evidence_is_sent_and_timestamp_is_retained(self, ollama):
        ollama.return_value = '{"title":"ドリルビットの確認","description":"電源を切り、チャックとビットを確認します。","tools":[],"warnings":[],"steps":[{"instruction":"電源を切り、チャックとドリルビットを確認します。"}]}'
        result = draft_procedure("DrillMachine.mp4", self.excerpts, "ja")
        prompt = ollama.call_args.args[0]
        self.assertIn(self.excerpts[0]["text"], prompt)
        self.assertIn("SOURCE REF: DrillMachine.mp4 · 00:12", prompt)
        self.assertEqual(result["steps"][0]["timestamp"], "00:12")
        self.assertEqual(result["steps"][0]["source_ref"], "DrillMachine.mp4 · 00:12")

    @patch("app.ai.ollama")
    def test_unrelated_subject_is_rejected(self, ollama):
        ollama.return_value = '{"title":"User-Facing SOP for Setting Up a Virtual Environment","description":"Create a Python virtual environment.","tools":["Python"],"warnings":[],"steps":[{"instruction":"Open a command-line interface as administrator and navigate directories."}]}'
        with self.assertRaisesRegex(ValueError, "did not sufficiently match"):
            draft_procedure("DrillMachine.mp4", self.excerpts, "en")

    @patch("app.ai.ollama")
    def test_insufficient_evidence_fails_without_fallback_sop(self, ollama):
        ollama.return_value = '{"insufficient_evidence":true,"reason":"Transcript is unclear."}'
        with self.assertRaisesRegex(ValueError, "Transcript is unclear"):
            draft_procedure("DrillMachine.mp4", self.excerpts, "en")

    def test_empty_evidence_does_not_call_model(self):
        with patch("app.ai.ollama") as ollama:
            with self.assertRaisesRegex(ValueError, "no usable"):
                draft_procedure("empty.mp4", [{"text": "", "source_ref": "00:01"}])
            ollama.assert_not_called()

    @patch("app.ai.ollama")
    def test_short_japanese_transcript_gets_quality_assessment(self, ollama):
        segments = [
            "ドリルの仕組みはとてもシンプルです", "ここがチャックです",
            "把をしっかり固定します", "モーターで高速回転させます", "これで穴は開きます",
        ]
        short_source = [{"text": text, "source_ref": f"DrillMachine.mp4 · 00:{i * 2:02d}", "timestamp": f"00:{i * 2:02d}"} for i, text in enumerate(segments)]
        ollama.return_value = '{"evidence_quality":"unusable","insufficient_evidence":true,"reason":"The action is not sufficiently clear to draft a reliable instruction."}'
        with self.assertRaisesRegex(ValueError, "not sufficiently clear"):
            draft_procedure("clip.mp4", short_source, "ja")
        ollama.assert_called_once()

    @patch("app.ai.ollama")
    def test_limited_supported_step_is_retained_as_limited(self, ollama):
        ollama.return_value = '{"evidence_quality":"limited","reason":"Only the described action is covered; setup and safety checks are missing.","title":"チャックを確認します","description":"作業前にチャックを確認します。","tools":[],"warnings":[],"steps":[{"instruction":"作業前にチャックを確認します。"}]}'
        source = [{"text": "作業前にチャックを確認します。", "source_ref": "clip.mp4 · 00:03", "timestamp": "00:03"}]
        result = draft_procedure("clip.mp4", source, "ja")
        self.assertEqual(result["evidence_quality"], "limited")
        self.assertEqual(result["steps"][0]["timestamp"], "00:03")

    def test_japanese_selection_reaches_whisper_and_timestamps_are_kept(self):
        calls = {}
        class FakeModel:
            def __init__(self, name, **kwargs):
                calls["model"] = (name, kwargs)
            def transcribe(self, path, **kwargs):
                calls["transcribe"] = (path, kwargs)
                return ([SimpleNamespace(text=" ドリルを確認します ", start=62.4, end=64.8)], SimpleNamespace(language="ja", language_probability=0.9))
        fake_module = ModuleType("faster_whisper")
        fake_module.WhisperModel = FakeModel
        with patch.dict(sys.modules, {"faster_whisper": fake_module}):
            segments, info = transcribe_video("/tmp/input.mp4", "ja", "DrillMachine.mp4")
        self.assertEqual(calls["transcribe"][1]["language"], "ja")
        self.assertEqual(calls["model"][1], {"device": "cpu", "compute_type": "int8"})
        self.assertEqual((segments[0]["start_seconds"], segments[0]["end_seconds"]), (62, 64))
        self.assertEqual(segments[0]["source_ref"], "DrillMachine.mp4 · 01:02")
        self.assertEqual(info.language, "ja")

    def test_source_id_isolation_uses_only_selected_chunks(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        with Session(engine) as db:
            db.add_all([
                Source(id=7, source_type="video", filename="first.mp4", file_path="first.mp4"),
                Source(id=11, source_type="video", filename="second.mp4", file_path="second.mp4"),
            ])
            db.flush()
            db.add_all([
                KnowledgeChunk(source_id=7, text="first transcript", source_ref="first · 00:01", start_seconds=1, end_seconds=2, embedding_json="[]"),
                KnowledgeChunk(source_id=11, text="second transcript", source_ref="second · 00:03", start_seconds=3, end_seconds=4, embedding_json="[]"),
            ])
            db.flush()
            excerpts = load_source_excerpts(db, 11)
        self.assertEqual([item["text"] for item in excerpts], ["second transcript"])
        self.assertEqual(excerpts[0]["source_id"], 11)
        self.assertEqual(excerpts[0]["timestamp"], "00:03")
        engine.dispose()


if __name__ == "__main__":
    unittest.main()
