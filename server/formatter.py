import subprocess


def format_code_range(file_path, start_line, start_column, end_line, end_column):
    # read contents from file
    lineno = 1
    contents = []
    with open(file_path, "r") as f:
        while lineno < start_line:
            lineno += 1
            f.readline()
        while lineno <= end_line:
            lineno += 1
            contents.append(f.readline())
    contents[0] = contents[0][start_column - 1 :]
    contents[-1] = contents[-1][:end_column]

    code = "".join(contents)

    cmd_list = ["clang-format", "--style=LLVM"]
    p = subprocess.Popen(
        cmd_list,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    stdout, stderr = p.communicate(code.encode())
    if p.returncode != 0:
        return None
    return stdout.decode()


def format_code(file_path):
    cmd_list = ["clang-format", "--style=LLVM", file_path]
    p = subprocess.Popen(
        cmd_list,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    stdout, stderr = p.communicate()
    if p.returncode != 0:
        return None
    return stdout.decode()


def main():
    import os

    file_path = os.path.join(os.path.dirname(__file__), "sample.asy")
    code_formatted = format_code_range(file_path, 3, 4, 4, 11)
    print(code_formatted)


if __name__ == "__main__":
    main()
