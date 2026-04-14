"""
Tests pour le Intent Classifier
"""
import pytest
from semantic.intent_classifier import (
    IntentClassifier, SemanticResult, IntentType
)


class TestMockClassifier:
    def setup_method(self):
        self.classifier = IntentClassifier(use_llm=False)
        self.classifier.initialize()

    def test_classify_create(self):
        result = self.classifier.classify("Créer une nouvelle tâche")
        assert result.intent == IntentType.CREATE
        assert "task" in result.topics
        assert result.use_mock

    def test_classify_approve(self):
        result = self.classifier.classify("Approuver la demande T-123")
        assert result.intent == IntentType.APPROVE
        assert "approval" in result.topics
        assert "T-123" in str(result.entities)

    def test_classify_reject(self):
        result = self.classifier.classify("Rejeter cette requête")
        assert result.intent == IntentType.REJECT

    def test_classify_query(self):
        result = self.classifier.classify("Quel est le statut?")
        assert result.intent == IntentType.QUERY

    def test_classify_cancel(self):
        result = self.classifier.classify("Annuler l'opération")
        assert result.intent == IntentType.CANCEL

    def test_classify_entities_extraction(self):
        result = self.classifier.classify("Traiter T-456 et ID-789")
        assert "task_ids" in result.entities or "ids" in result.entities

    def test_confidence_score(self):
        result = self.classifier.classify("Approuver la tâche")
        assert 0.0 <= result.confidence <= 1.0

    def test_batch_classify(self):
        messages = [
            "Créer une tâche",
            "Approuver la demande",
            "Quel est le statut?"
        ]
        results = self.classifier.batch_classify(messages)
        assert len(results) == 3
        assert all(isinstance(r, SemanticResult) for r in results)


class TestSemanticResult:
    def test_to_context(self):
        result = SemanticResult(
            intent=IntentType.APPROVE,
            topics=["approval", "task"],
            entities={"id": "T-123"},
            confidence=0.9,
            raw_reasoning="Test"
        )
        
        context = result.to_context()
        assert context["intent"] == "APPROVE"
        assert context["topics"] == ["approval", "task"]
        assert context["confidence"] == 0.9
