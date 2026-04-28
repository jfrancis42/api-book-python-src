import sys
import importlib.metadata


def check_python():
    v = sys.version_info
    ok = v >= (3, 10)
    label = "OK  " if ok else "FAIL"
    suffix = "" if ok else "  (need 3.10 or later)"
    print(f"{label}  Python {v.major}.{v.minor}.{v.micro}{suffix}")
    return ok


def check_package(import_name, dist_name=None):
    dist_name = dist_name or import_name
    try:
        __import__(import_name)
        version = importlib.metadata.version(dist_name)
        print(f"OK    {dist_name} {version}")
        return True
    except ImportError:
        print(f"FAIL  {dist_name} -- run: pip install {dist_name}")
        return False
    except importlib.metadata.PackageNotFoundError:
        print(f"OK    {dist_name} (version unknown)")
        return True


if __name__ == "__main__":
    passed = check_python()

    for pkg in sys.argv[1:]:
        # "dotenv:python-dotenv" handles packages whose import name
        # differs from their distribution (PyPI) name.
        if ":" in pkg:
            import_name, dist_name = pkg.split(":", 1)
        else:
            import_name = dist_name = pkg
        passed = check_package(import_name, dist_name) and passed

    print()
    if passed:
        print("All checks passed.")
    else:
        print("One or more checks failed. See above.")
        sys.exit(1)
