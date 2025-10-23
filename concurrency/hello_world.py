import subprocess
import time


def sequential():
    for i in range(5):
        result = subprocess.run(
            f"python test.py && echo 'Hello from child {i}'",
            capture_output=True,
            encoding="utf-8",
            shell=True,
        )

        print(result)
        print(result.check_returncode())
        print(result.stdout)


def parallel():
    processes = []
    for i in range(5):
        p = subprocess.Popen(
            f"python ./test.py && echo 'Hello from child {i}'",
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        processes.append((i, p))

    print(processes)

    start = time.perf_counter()
    for i, p in processes:
        print(f"Waiting communicate {i}")
        out, err = p.communicate()
        print(f"[Child{i}] Output:\n{out}")

    delta = time.perf_counter() - start

    print(f"Finished in {delta:.3} seconds")


# sequential()
parallel()
