# =============================================================================
# HYDRA-UMC-COGNITIVE-NODE - tests/test_confirmation_proof.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The ConfirmationProof of the SDK: the same bytes, signed when a key is given and asked for only when switched on."""

import os
import tempfile
import time
import unittest
from pathlib import Path

from hydra_umc_cognitive_node.confirmation_proof import proof_identifier, sign_proof, verify_proof
from hydra_umc_cognitive_node.autonomy import AutonomyConfigError, AutonomyPolicy, parse_autonomy_config

KEY = b"vector-key-" + b"0123456789abcdef" * 2


class Proof(unittest.TestCase):
    def test_the_proof_is_the_one_of_the_sdk(self):
        for (kind, action, subject, operator, identity), signature in (
            (("approval", "f" * 64, "robot-1", "ana", "a" * 32), "40455c91e510cecef1a7f2705b206587cb7211b464862ce8a35c1fe500048477"),
            (("voice", "turn-42", "installation", proof_identifier("ana@example.com"), "b" * 32), "6d353d430780ae4a8d56cc6e062cd934998f0813b870e69887059f49fda5a281"),
        ):
            proof = sign_proof(KEY, kind=kind, action_id=action, subject_id=subject, operator=operator, approved_at_ms=1700000000000,
                               expires_at_ms=1700000010000, approval_id=identity)
            self.assertEqual(proof["signature"], signature)
            self.assertEqual(verify_proof(KEY, proof, expected_action_id=action, expected_subject_id=subject, now_ms=1700000000500), (True, ""))
            self.assertFalse(verify_proof(KEY, proof, expected_action_id=action, expected_subject_id="robot-2", now_ms=1700000000500)[0])
            self.assertFalse(verify_proof(KEY, proof, expected_action_id=action, expected_subject_id=subject, now_ms=1700000010000)[0])
            self.assertFalse(verify_proof(b"x" * 32, proof, expected_action_id=action, expected_subject_id=subject, now_ms=1700000000500)[0])

    def test_the_node_asks_for_the_proof_only_when_switched_on(self):
        question = {"source": "vla", "kind": "move", "actionId": "f" * 64, "level": "execute_with_confirmation", "humanConfirmed": True}
        sources = {"vla": "execute_with_confirmation"}
        off = AutonomyPolicy(parse_autonomy_config({"enabled": True, "sources": sources}))
        self.assertEqual(off.evaluate(question)["decision"], "allow")
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "approval.key"
            path.write_bytes(KEY)
            os.chmod(path, 0o600)
            on = AutonomyPolicy(parse_autonomy_config({"enabled": True, "sources": sources, "confirmationProof": {"required": True, "approvalKeyFile": str(path)}}))
        self.assertEqual(on.evaluate(question)["reason"], "proof_required")
        now = int(time.time() * 1000)
        proof = sign_proof(KEY, kind="approval", action_id="f" * 64, subject_id="robot-1", operator="ana", approved_at_ms=now, expires_at_ms=now + 10000, approval_id="c" * 32)
        self.assertEqual(on.evaluate(dict(question, subjectId="robot-2", confirmationProof=proof))["reason"], "proof_invalid")
        self.assertEqual(on.evaluate(dict(question, confirmationProof=proof))["reason"], "proof_invalid")
        self.assertEqual(on.evaluate(dict(question, subjectId="robot-1", confirmationProof=proof))["decision"], "allow")
        self.assertEqual(on.evaluate(dict(question, subjectId="robot-1", confirmationProof=proof))["reason"], "proof_invalid")  # only once
        with self.assertRaises(AutonomyConfigError):
            parse_autonomy_config({"confirmationProof": {"required": True}})


if __name__ == "__main__":
    unittest.main()
