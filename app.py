import json
import os
import re
from datetime import datetime, timedelta

import redis
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel

TIME_PATTERN = "%H:%M:%S %d.%m.%Y"


class LinksArray(BaseModel):
    links: list[str]


r = redis.Redis(
    host=os.environ.get("REDIS_HOST", "localhost"),
    port=os.environ.get("REDIS_PORT", 6379),
    db=os.environ.get("REDIS_DB", 0),
    encoding="utf-8",
    decode_responses=True
)
app = FastAPI(
    debug=os.environ.get("APP_DEBUG", True),
)


def get_domain_from_link(link: str):
    matching = re.findall(r'^(https?://|^)(?:www\.|)([\w.-]+).*', link)
    return matching[0][1]


@app.get("/visited_links/")
def get_visited_links(from_: int = 0, to_: int = 0):
    if from_ == 0 or to_ == 0:
        query_error = {
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
        return JSONResponse(content=query_error, status_code=400)
    elif to_ > from_:
        to_greater_than_from_error = {
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
        return JSONResponse(content=to_greater_than_from_error, status_code=400)

    now = datetime.now()
    yesterday = now - timedelta(days=1)

    from_date = now.timestamp() if from_ == 0 else from_
    to_date = yesterday.timestamp() if to_ == 0 else to_

    timestamp_range = list(range(int(to_date), int(from_date)))
    all_data = r.mget(timestamp_range)
    filter_all_data = list(filter(lambda x: x is not None, all_data))
    domains = set()
    for el in filter_all_data:
        split_elements = el.split(',')
        for i in split_elements:
            domains.add(i)

    return JSONResponse(content={"domains": list(domains), "status": "ok"}, status_code=200)


@app.post("/visited_links/")
def post_visited_links(links_array: LinksArray):
    links_array_as_dict = json.loads(links_array.json())
    links = links_array_as_dict.get("links")
    now_timestamp = int(datetime.now().timestamp())
    domains = set()
    for link in links:
        domains.add(get_domain_from_link(link=link))

    set_to_str = ','.join(domains)
    r.mset({now_timestamp: set_to_str})

    return JSONResponse(content={"status": "ok"}, status_code=200)
