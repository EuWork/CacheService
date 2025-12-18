from unittest.mock import Mock

import pytest

from service import CacheService

def test_cache_hit_returns_value_from_redis_and_does_not_call_compute():
    redis_mock = Mock()
    redis_mock.get.return_value = b"cached-value"

    service = CacheService(redis_client=redis_mock)
    compute_mock = Mock(return_value="computed-value")

    result = service.get_or_compute("test-key", compute_mock)

    # Assert: вернули значение из кэша
    assert result == "cached-value"

    # compute_func НЕ должен вызываться при cache hit
    compute_mock.assert_not_called()

    # Redis: только get, без setex
    redis_mock.get.assert_called_once_with("test-key")
    redis_mock.setex.assert_not_called()


def test_cache_miss_computes_value_and_writes_to_cache():
    redis_mock = Mock()
    # кэш-мисс: в Redis ничего нет
    redis_mock.get.return_value = None

    service = CacheService(redis_client=redis_mock)
    compute_mock = Mock(return_value="computed-value")

    result = service.get_or_compute("key-123", compute_mock)

    # Assert: вернули вычисленное значение
    assert result == "computed-value"
    compute_mock.assert_called_once_with()

    # Redis: сначала get, потом setex с TTL = 60 (как в сервисе)
    redis_mock.get.assert_called_once_with("key-123")
    redis_mock.setex.assert_called_once_with("key-123", 60, "computed-value")


def test_redis_get_failure_raises_error_and_does_not_call_compute():
    redis_mock = Mock()
    # имитируем падение Redis при чтении
    redis_mock.get.side_effect = RuntimeError("Redis is down")

    service = CacheService(redis_client=redis_mock)
    compute_mock = Mock(return_value="computed-after-failure")

    with pytest.raises(RuntimeError, match="Redis is down"):
        service.get_or_compute("key", compute_mock)

    # compute_func НЕ должен вызываться, так как упали на get()
    compute_mock.assert_not_called()
    redis_mock.get.assert_called_once_with("key")


def test_redis_set_failure_still_computes_value_but_raises_on_write():
    redis_mock = Mock()
    redis_mock.get.return_value = None
    # падение при записи в Redis
    redis_mock.setex.side_effect = RuntimeError("Write failed")

    service = CacheService(redis_client=redis_mock)
    compute_mock = Mock(return_value="computed")

    # Act + Assert: значение считается, но при записи в Redis вылетает исключение
    with pytest.raises(RuntimeError, match="Write failed"):
        service.get_or_compute("key", compute_mock)

    # compute_func должен был вызваться
    compute_mock.assert_called_once_with()

    # get был вызван
    redis_mock.get.assert_called_once_with("key")
    # setex тоже пытались вызвать
    redis_mock.setex.assert_called_once_with("key", 60, "computed")
