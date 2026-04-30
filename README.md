# Source Code — *Requests Granted*

This repository contains the complete, runnable source code for every chapter
of *Requests Granted: Crafting REST API Clients and Servers in Python* by
George Jeffrey Francis (Ordo Artificum Press, 2026).

**The book is available on Amazon:**
https://www.amazon.com/dp/PLACEHOLDER

---

## Organization

Each directory corresponds to a chapter and is **self-contained** — you can
run the code in any chapter's directory without copying files from other
chapters.

| Directory | Chapter |
|-----------|---------|
| `ch00_before_you_begin/` | Chapter 0: Before You Begin |
| `ch01_what_is_an_api/` | *(no runnable code)* |
| `ch02_what_is_rest/` | *(no runnable code)* |
| `ch03_devtools/` | Chapter 3: Reverse-Engineering APIs with Browser DevTools |
| `ch04_first_call/` | Chapter 4: Your First API Call |
| `ch05_json/` | Chapter 5: JSON — The Common Tongue |
| `ch06_credentials/` | Chapter 6: Keeping Secrets |
| `ch07_parameters/` | Chapter 7: Query Parameters and Path Parameters |
| `ch08_sending_data/` | Chapter 8: Sending Data |
| `ch09_errors/` | Chapter 9: Handling Errors Gracefully |
| `ch10_rate_limits/` | Chapter 10: Rate Limits |
| `ch11_retrying/` | Chapter 11: Retrying with Exponential Backoff |
| `ch12_pagination/` | Chapter 12: Pagination |
| `ch13_http_caching/` | Chapter 13: HTTP Caching — Conditional Requests |
| `ch14_sessions/` | Chapter 14: Sessions, Timeouts, and Connection Management |
| `ch15_threading/` | Chapter 15: Running API Calls in Threads |
| `ch16_async/` | Chapter 16: Async API Calls with httpx |
| `ch17_testing/` | Chapter 17: Testing Code That Calls APIs |
| `ch18_xml/` | Chapter 18: XML — The Other Data Format |
| `ch19_auth/` | Chapter 19: Authentication Deep Dive |
| `ch20_oauth/` | Chapter 20: OAuth 2.0 |
| `ch21_webhooks/` | Chapter 21: Webhooks — Receiving Events from GitHub |
| `ch22_complete_client/` | Chapter 22: The Complete Client |
| `ch23_fastapi_intro/` | Chapter 23: Introduction to FastAPI |
| `ch24_openapi/` | Chapter 24: OpenAPI |
| `ch25_first_endpoint/` | Chapter 25: Path Parameters and Response Models |
| `ch26_pydantic/` | Chapter 26: Data Modeling with Pydantic |
| `ch27_database/` | Chapter 27: Databases with SQLAlchemy |
| `ch28_routers/` | Chapter 28: Organizing with Routers |
| `ch29_post/` | Chapter 29: POST and Creating Resources |
| `ch30_put_patch_delete/` | Chapter 30: PUT, PATCH, and DELETE |
| `ch31_errors/` | Chapter 31: Error Responses |
| `ch32_json_api/` | Chapter 32: The JSON:API Specification |
| `ch33_pagination/` | Chapter 33: Pagination in the Server |
| `ch34_api_versioning/` | Chapter 34: API Versioning |
| `ch35_auth/` | Chapter 35: Authentication in FastAPI |
| `ch36_rate_limiting/` | Chapter 36: Rate Limiting |
| `ch37_search/` | Chapter 37: Search Endpoints |
| `ch38_files/` | Chapter 38: File Upload and Download |
| `ch39_webhooks_server/` | Chapter 39: Sending Webhooks from the Server |
| `ch40_testing_fastapi/` | Chapter 40: Testing FastAPI |
| `ch41_postgres_async/` | Chapter 41: PostgreSQL and Async SQLAlchemy |
| `ch42_observability/` | Chapter 42: Observability |
| `ch43_deploying/` | Chapter 43: Deploying FastAPI |
| `ch44_complete_server/` | Chapter 44: The Complete Server |

---

## Getting Started

Most chapters in Part I require a GitHub personal access token. Create a
`.env` file in each chapter directory you want to run:

```
GITHUB_TOKEN=your_token_here
```

Part II (chapters 23–44) runs entirely on your local machine and does not
require a token.

Install dependencies with:

```bash
pip install -r requirements.txt
```

A `requirements.txt` is included at the top level of the book's source tree;
each chapter directory also lists only the packages it actually uses.
