import pytest
import uuid

from core.domain.ai.entities import Embedding, AIResult, AITask
from core.domain.ai.value_objects import AIProvider, ModelConfig, TaskStatus


def test_embedding_creation():
    emb = Embedding(
        id="emb-1",
        vector=(0.1, 0.2, 0.3),
        content_id=uuid.uuid4(),
        model="gpt-4o",
    )
    assert emb.id == "emb-1"
    assert emb.dimensions == 3


def test_embedding_auto_dimensions():
    emb = Embedding(
        id="emb-1",
        vector=(0.1, 0.2, 0.3, 0.4),
        content_id=uuid.uuid4(),
    )
    assert emb.dimensions == 4


def test_embedding_empty_vector_raises():
    with pytest.raises(ValueError):
        Embedding(
            id="emb-1",
            vector=(),
            content_id=uuid.uuid4(),
        )


def test_embedding_magnitude():
    emb = Embedding(
        id="emb-1",
        vector=(3.0, 4.0),
        content_id=uuid.uuid4(),
    )
    assert emb.magnitude == 5.0


def test_embedding_normalized():
    emb = Embedding(
        id="emb-1",
        vector=(3.0, 4.0),
        content_id=uuid.uuid4(),
    )
    norm = emb.normalized()
    assert abs(norm.magnitude - 1.0) < 1e-10


def test_ai_result_creation():
    result = AIResult(
        id=uuid.uuid4(),
        output={"key": "value"},
        token_usage=100,
        latency_ms=500.0,
        cost_usd=0.005,
        model_version="gpt-4o-2024-08-06",
        confidence=0.95,
    )
    assert result.token_usage == 100
    assert result.confidence == 0.95


def test_ai_result_tokens_per_second():
    result = AIResult(token_usage=1000, latency_ms=500.0)
    assert result.tokens_per_second == 2000.0


def test_ai_result_tokens_per_second_zero_latency():
    result = AIResult(token_usage=1000, latency_ms=0.0)
    assert result.tokens_per_second == 0.0


def test_ai_task_creation():
    task = AITask(
        id=uuid.uuid4(),
        task_type="classification",
        provider=AIProvider.OPENAI,
        model_config=ModelConfig(provider=AIProvider.OPENAI, model_name="gpt-4o"),
    )
    assert task.task_type == "classification"
    assert task.status == TaskStatus.PENDING
    assert not task.is_running


def test_ai_task_start():
    task = AITask(id=uuid.uuid4(), task_type="classification")
    task.start()
    assert task.status == TaskStatus.RUNNING
    assert task.is_running
    assert task.started_at is not None


def test_ai_task_complete():
    task = AITask(id=uuid.uuid4(), task_type="classification")
    task.start()
    result_id = uuid.uuid4()
    task.complete(result_id)
    assert task.status == TaskStatus.COMPLETED
    assert task.result_id == result_id
    assert task.completed_at is not None


def test_ai_task_fail():
    task = AITask(id=uuid.uuid4(), task_type="classification")
    task.start()
    task.fail("Model timeout")
    assert task.status == TaskStatus.FAILED
    assert task.error_message == "Model timeout"
    assert task.completed_at is not None


def test_ai_task_cancel():
    task = AITask(id=uuid.uuid4(), task_type="classification")
    task.start()
    task.cancel()
    assert task.status == TaskStatus.CANCELLED
    assert task.completed_at is not None


def test_ai_task_duration_ms():
    task = AITask(id=uuid.uuid4(), task_type="classification")
    assert task.duration_ms is None  # no start/completion
    task.start()
    task.complete(uuid.uuid4())
    assert task.duration_ms is not None
    assert task.duration_ms >= 0
