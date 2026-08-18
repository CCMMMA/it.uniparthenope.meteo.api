# Python API Tutorial

## Who This Tutorial Is For

This tutorial is written for high-school students and first-year STEM university students who know a little Python and want to learn how to work with a real web API.

We will go step by step:

1. understand what an API is
2. send our first request
3. read JSON data
4. search for places
5. request forecasts
6. download a CSV file
7. save an image from the API

The code examples use the Python `requests` library because it is simple and widely used.

Related documents:

- Endpoint reference: [API_ENDPOINTS.md](API_ENDPOINTS.md)
- Android/Kotlin tutorial: [ANDROID_KOTLIN_API_TUTORIAL.md](ANDROID_KOTLIN_API_TUTORIAL.md)
- iOS/Swift tutorial: [IOS_SWIFT_API_TUTORIAL.md](IOS_SWIFT_API_TUTORIAL.md)

The governed API is available under `/api/v1`. Product discovery and metadata
now have versioned equivalents; for new code, begin with:

```python
products = requests.get(f"{BASE_URL}/api/v1/products", timeout=10)
products.raise_for_status()
print(products.json()["products"])
```

Existing legacy examples remain supported while additional resource families
receive documented versioned equivalents.

## 1. What Is An API?

API stands for Application Programming Interface.

In simple words:

- a website is usually made for people
- an API is usually made for programs

When we call this API, we ask a server for meteorological information such as:

- version data
- legal text
- place information
- forecasts
- time series
- images

## 2. What You Need

You need:

- Python 3
- internet access to the running API
- the `requests` package

Install `requests` if needed:

```bash
pip install requests
```

## 3. Our First Python Script

Create a file called `hello_api.py`:

```python
import os
import requests

BASE_URL = "https://api.meteo.uniparthenope.it"

response = requests.get(f"{BASE_URL}/version")
print("Status code:", response.status_code)
print("JSON:", response.json())
```

What happens here:

- `requests.get(...)` sends an HTTP `GET` request
- `response.status_code` tells us if the request worked
- `response.json()` converts the JSON response into Python data

Possible output:

```python
Status code: 200
JSON: {'version': '4.01', 'environment': 'production'}
```

## 4. Reading JSON Like Python Data

JSON objects become Python dictionaries.

Example:

```python
import os
import requests

BASE_URL = "https://api.meteo.uniparthenope.it"

data = requests.get(f"{BASE_URL}/version").json()

print("Version:", data["version"])
print("Environment:", data["environment"])
```

This is useful because many endpoints in this API return JSON.

## 5. Searching For A Place

Let us search for a place by name:

```python
import requests

BASE_URL = "https://api.meteo.uniparthenope.it"

name = "Napoli"
response = requests.get(f"{BASE_URL}/places/search/byname/{name}")

print("Status:", response.status_code)
places = response.json()
print("Number of results:", len(places))

for place in places[:5]:
    print(place.get("id"), place.get("name"))
```

What we learn:

- the endpoint returns a list
- each item is a place object
- we can inspect the `id` to use it in later requests

## 6. Using Autocomplete

Autocomplete endpoints are great for interactive apps.

```python
import requests

BASE_URL = "https://api.meteo.uniparthenope.it"

response = requests.get(
    f"{BASE_URL}/places/search/byname/autocomplete",
    params={"term": "nap"}
)

results = response.json()
for item in results:
    print(item["id"], "-", item["label"])
```

Important idea:

- the `params={...}` argument adds query parameters to the URL

So Python builds a URL similar to:

```text
https://api.meteo.uniparthenope.it/places/search/byname/autocomplete?term=nap
```

## 7. Getting A Forecast

Suppose we want a forecast for a product and a place.

Example product:

- `wrf5`

Example place:

- `com63049`

```python
import os
import requests

BASE_URL = "https://api.meteo.uniparthenope.it"

product = "wrf5"
place = "com63049"

response = requests.get(
    f"{BASE_URL}/api/v1/products/{product}/forecast/{place}",
    headers={"X-API-Key": os.environ["METEO_API_KEY"]},
)
forecast_data = response.json()

print("Top-level keys:", forecast_data.keys())
```

This is a good debugging habit:

- first print the top-level keys
- then inspect the structure before trying to use every value

## 8. Pretty Printing JSON

Sometimes API data is large. Let us print it nicely:

```python
import requests
import json

BASE_URL = "https://api.meteo.uniparthenope.it"

response = requests.get(f"{BASE_URL}/products/wrf5/forecast/com63049")
data = response.json()

print(json.dumps(data, indent=2))
```

`indent=2` makes the output easier to read.

## 9. Reading A Time Series

A time series gives values over time.

```python
import os
import requests

BASE_URL = "https://api.meteo.uniparthenope.it"

response = requests.get(
    f"{BASE_URL}/api/v1/products/ww33/timeseries/ca001",
    headers={"X-API-Key": os.environ["METEO_API_KEY"]},
)
data = response.json()

print("Keys:", data.keys())

timeseries = data.get("timeseries", [])
print("Number of time steps:", len(timeseries))

if timeseries:
    print("First time step:", timeseries[0])
```

This teaches an important idea:

- use `.get("key", default)` when you are not completely sure a key is present

That makes your program safer.

## 10. Downloading CSV Data

Some endpoints return CSV instead of JSON.

We should use `response.text` for that:

```python
import requests

BASE_URL = "https://api.meteo.uniparthenope.it"

response = requests.get(f"{BASE_URL}/products/wrf5/timeseries/ca001/csv")

print("Status:", response.status_code)
print("Content-Type:", response.headers.get("Content-Type"))
print(response.text[:300])
```

If you want to save the CSV file:

```python
import requests

BASE_URL = "https://api.meteo.uniparthenope.it"

response = requests.get(f"{BASE_URL}/products/wrf5/timeseries/ca001/csv")

with open("timeseries.csv", "w", encoding="utf-8") as f:
    f.write(response.text)

print("Saved timeseries.csv")
```

## 11. Downloading An Image

Some endpoints return binary data, such as PNG images.

For example:

```python
import requests

BASE_URL = "https://api.meteo.uniparthenope.it"

response = requests.get(f"{BASE_URL}/products/ww33/forecast/ca001/plot/image")

with open("forecast_plot.png", "wb") as f:
    f.write(response.content)

print("Saved forecast_plot.png")
```

Important:

- use `"wb"` for binary files
- use `response.content`, not `response.text`

## 12. Adding Error Checks

Real programs should not assume everything always works.

Safer example:

```python
import requests

BASE_URL = "https://api.meteo.uniparthenope.it"

try:
    response = requests.get(f"{BASE_URL}/version", timeout=10)
    response.raise_for_status()
    data = response.json()
    print("Version:", data["version"])
except requests.exceptions.RequestException as e:
    print("Network or HTTP error:", e)
except ValueError:
    print("The server did not return valid JSON.")
```

Why this is good:

- `timeout=10` prevents your program from waiting forever
- `raise_for_status()` turns HTTP errors into Python exceptions
- `except` blocks help you understand failures

## 13. Building Reusable Functions

Now let us organize our code better.

```python
import requests

BASE_URL = "https://api.meteo.uniparthenope.it"


def get_json(path, params=None):
    response = requests.get(f"{BASE_URL}{path}", params=params, timeout=15)
    response.raise_for_status()
    return response.json()


version = get_json("/version")
print("Version:", version["version"])

places = get_json("/places/search/byname/Napoli")
print("Results:", len(places))
```

This is better because:

- we avoid repeating the same code
- our programs become easier to maintain

## 14. A Small Mini-Project

Let us create a mini-project:

Goal:

1. search for a place
2. pick the first result
3. ask for a forecast
4. print some useful information

```python
import requests

BASE_URL = "https://api.meteo.uniparthenope.it"


def get_json(path, params=None):
    response = requests.get(f"{BASE_URL}{path}", params=params, timeout=15)
    response.raise_for_status()
    return response.json()


search_name = "Napoli"
places = get_json(f"/places/search/byname/{search_name}")

if not places:
    print("No places found.")
    raise SystemExit

first_place = places[0]
place_id = first_place["id"]
print("Using place:", place_id)

forecast = get_json(f"/products/wrf5/forecast/{place_id}")
print("Forecast keys:", forecast.keys())
```

This is the kind of logic used in real apps:

- first discover the resource
- then use its identifier for the next call

## 15. Working With Query Parameters

Some endpoints accept query parameters such as `date`.

Example:

```python
import requests

BASE_URL = "https://api.meteo.uniparthenope.it"

response = requests.get(
    f"{BASE_URL}/products/wrf5/forecast/com63049",
    params={"date": "20250317Z1200"},
    timeout=15
)

print(response.url)
print(response.status_code)
print(response.json())
```

This is a very important API skill:

- path parameters go inside the URL path
- query parameters go in `params={...}`

## 16. Saving JSON To A File

This is useful for analysis or homework.

```python
import requests
import json

BASE_URL = "https://api.meteo.uniparthenope.it"

data = requests.get(f"{BASE_URL}/version", timeout=15).json()

with open("version.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)

print("Saved version.json")
```

## 17. Common Beginner Mistakes

### Mistake 1: using `response.text` for JSON

Better:

- use `response.json()` for JSON

### Mistake 2: using `response.json()` for images

Better:

- use `response.content` for images

### Mistake 3: forgetting timeouts

Better:

- use `timeout=10` or `timeout=15`

### Mistake 4: assuming all requests succeed

Better:

- check `status_code`
- or use `raise_for_status()`

## 18. A Full Beginner Script

This final script combines several ideas:

```python
import json
import requests

BASE_URL = "https://api.meteo.uniparthenope.it"


def get_json(path, params=None, headers=None):
    response = requests.get(
        f"{BASE_URL}{path}",
        params=params,
        headers=headers,
        timeout=15
    )
    response.raise_for_status()
    return response.json()


def main():
    version = get_json("/version")
    print("API version:", version["version"])

    places = get_json("/places/search/byname/Napoli")
    if not places:
        print("No places found.")
        return

    place_id = places[0]["id"]
    print("Selected place:", place_id)

    forecast = get_json(f"/products/wrf5/forecast/{place_id}")
    print("Forecast received.")

    with open("forecast.json", "w", encoding="utf-8") as f:
        json.dump(forecast, f, indent=2)

    print("Saved forecast.json")


if __name__ == "__main__":
    main()
```

## 19. What To Try Next

After you finish this tutorial, try:

1. search for a different city
2. request a time series instead of a forecast
3. download a plot image
4. save CSV data to a file
5. compare two different product codes

## 20. Summary

You learned how to:

- send HTTP requests with Python
- read JSON data
- use path parameters
- use query parameters
- save CSV and image files
- handle basic errors
- organize your code with functions

That is already a strong foundation for real scientific computing, web programming, and data analysis projects.

## Related Documentation

- [API_ENDPOINTS.md](API_ENDPOINTS.md)
- [OPERATIONS_AND_USAGE.md](OPERATIONS_AND_USAGE.md)
- [PRODUCTION_SETUP.md](PRODUCTION_SETUP.md)
