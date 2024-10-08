# Boot.Dev search
#### A *(not official)* CLI [Boot.Dev](https://www.boot.dev/) lessons search engine

### Installation
1. Clone repo
    ```
    git clone https://github.com/eeyako/bootdev-search.git
    ```
2. Create virtual environment within directory
    ```
    cd bootdev-search/ && python3 -m venv venv
    ```
3. Activate virtual environment
    ```
    source venv/bin/activate
    ```
4. Install requirements
    ```
    pip install -r requirements.txt
    ```

### How to use
```
usage: main.py [-h] [--index] [--indexed-languages] [--languages LANGUAGES [LANGUAGES ...]] [search]

Boot.Dev search

positional arguments:
  search                a string to search

options:
  -h, --help            show this help message and exit
  --index, -i           scrape and index boot.dev lessons, takes a while
  --indexed-languages, -il
                        prints the currently indexed languages and their last index date
  --languages LANGUAGES [LANGUAGES ...], -l LANGUAGES [LANGUAGES ...]
                        which programming languages to limit the search or indexing to
```

### Important
Program **needs** to index before first search, which could take up to 5 mins.
Once indexed, a search can be ran immediately.
