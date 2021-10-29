from datetime import datetime
from unittest import mock

from fastapi.testclient import TestClient

from app import app, get_domain_from_link


class MockingRedis:

    def __init__(self):
        self.save_redis = {}

    def get(self, key):
        return self.save_redis.get(key)

    @property
    def get_first_key(self):
        return list(self.save_redis.keys())[0]

    def mset(self, key):
        self.save_redis.update(key)

    def mget(self, keys):
        return [self.save_redis.get(key) for key in keys]

    def __len__(self):
        return len(self.save_redis)


valid_post_data = {
    "links": [
        "ya.ru",
        "funbox.ru"
    ]
}

invalid_post_data = {
    "links": 1
}

client = TestClient(app)
redis_mock = MockingRedis()


def test_func_get_domain_from_link():
    links = [
        "http://ya.ru",
        "https://ya.ru?q=123",
        "funbox.ru",
        "https://stackoverflow.com/questions/11828270/how-to-exit-the-vim-editor"
    ]
    domains = [get_domain_from_link(link) for link in links]
    assert domains == [
        "ya.ru",
        "ya.ru",
        "funbox.ru",
        "stackoverflow.com",
    ]


@mock.patch('redis.Redis.mset', side_effect=redis_mock.mset)
def test_post_visited_links_with_valid_query(mock_redis_mset):
    response = client.post("/visited_links/", json=valid_post_data)
    now = int(datetime.now().timestamp())
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert now in redis_mock.save_redis
    assert len(redis_mock.get(now).split(',')) == 2


@mock.patch('redis.Redis.mset', side_effect=redis_mock.mset)
def test_post_visited_links_with_invalid_query(mock_redis_mset):
    response = client.post("/visited_links/", json=invalid_post_data)
    assert response.status_code == 422
    assert response.json() == {
        'detail': [
            {
                'loc': ['body', 'links'],
                'msg': 'value is not a valid list',
                'type': 'type_error.list'
            }
        ]
    }
    assert len(redis_mock) == 1


@mock.patch('redis.Redis.mget', side_effect=redis_mock.mget)
def test_get_visited_links_with_valid_query(mock_redis_mget):
    right_key = redis_mock.get_first_key
    response = client.get(f"/visited_links?from_={right_key + 1}&to_={right_key - 10}")
    json_response = response.json()
    assert response.status_code == 200
    assert len(json_response.keys()) == 2
    assert json_response.get("status") == "ok"
    assert len(json_response.get("domains")) == 2


@mock.patch('redis.Redis.mget', side_effect=redis_mock.mget)
def test_get_visited_links_to_greater_thank_from(mock_redis_mget):
    response = client.get("/visited_links?to_=1635502327&from_=1635502200")
    assert response.status_code == 400
    assert response.json() == {
        "detail": [
            {
                "loc": [
                    "query",
                    "to_",
                ],
                "status": "bad request",
                "msg": 'query parameter "to_" must be less than query parameter "from_"',
            }
        ]
    }


@mock.patch('redis.Redis.mget', side_effect=redis_mock.mget)
def test_get_visited_links_with_invalid_query(mock_redis_mget):
    response = client.get("/visited_links?to_=1635496510")
    assert response.status_code == 400
    assert response.json() == {
        "detail": [
            {
                "loc": [
                    "query",
                ],
                "status": "bad request",
                "msg": 'you need to pass two parameters "from_" and "to_", or none',
            }
        ]
    }
