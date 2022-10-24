import subprocess
import re


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
    clang_passed_text = stdout.decode()
    return asy_pass(clang_passed_text)


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
    clang_passed_text = stdout.decode()

    return asy_pass(clang_passed_text)


def asy_pass(clang_passed_text: str):
    clang_passed_text = clang_passed_text.replace("-- ", " --")

    # ^^ --clang-> ^ ^
    # ^ ^ --asy pass -> ^^ are needed
    reg = re.compile(r"\^[\t \r\n]*\^")
    clang_passed_text = reg.sub(r"^^", clang_passed_text)
    return clang_passed_text


def main():
    import os

    result = format_code(r"C:\mygithub\asy-lsp\server\sample.asy")


if __name__ == "__main__":
    main()
