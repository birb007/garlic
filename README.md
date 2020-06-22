# Garlic

An asynchronous API wrapper for [Onionoo](https://metrics.torproject.org/onionoo.html) using `anyio` and `asks`.

## Build Instructions

```terminal
$ git clone https://github.com/birb007/garlic.git
$ cd garlic
$ poetry build
$ pip install dist/garlic-0.1.0-py3-none-any.whl
```

You should now be able to import `garlic` from within Python.

### Builing Documentation

```terminal
$ cd docs
$ make html
```

The final documentation will be present in `docs/build/html`. Then you can open `index.html` in your browser of choice.
