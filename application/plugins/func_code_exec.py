
meta_info = {
                "name": "python",
                "description": "run a Python script and return the execution result.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "script": {
                            "type": "string",
                            "description": "Valid Python script to execute.",
                        }
                    },
                    "required": ["script"],
                },
            }

def func(**kwargs):
    import os
    from hashlib import md5
    import logging
    from autogen import oai
    from concurrent.futures import ThreadPoolExecutor, TimeoutError
    import subprocess
    import sys
    import pathlib
    CODE_BLOCK_PATTERN = r"```(\w*)\n(.*?)\n```"
    UNKNOWN = "unknown"
    TIMEOUT_MSG = "Timeout"
    DEFAULT_TIMEOUT = 600
    WIN32 = sys.platform == "win32"
    PATH_SEPARATOR = WIN32 and "\\" or "/"

    try:
        from termcolor import colored
    except ImportError:
        def colored(x, *args, **kwargs):
            return x
        
    def _cmd(lang):
        if lang.startswith("python") or lang in ["bash", "sh", "powershell"]:
            return lang
        if lang in ["shell"]:
            return "sh"
        if lang in ["ps1"]:
            return "powershell"
        
        raise NotImplementedError(f"{lang} not recognized in code execution")
    
    def infer_lang(code):
        """infer the language for the code.
        TODO: make it robust.
        """
        if code.startswith("python ") or code.startswith("pip") or code.startswith("python3 "):
            return "sh"

        # check if code is a valid python code
        try:
            compile(code, "test", "exec")
            return "python"
        except SyntaxError:
            # not a valid python code
            return UNKNOWN
        
    def run_code(code, **kwargs):
        """Run the code and return the result.

        Override this function to modify the way to run the code.
        Args:
            code (str): the code to be executed.
            **kwargs: other keyword arguments.

        Returns:
            A tuple of (exitcode, logs, image).
            exitcode (int): the exit code of the code execution.
            logs (str): the logs of the code execution.
            image (str or None): the docker image used for the code execution.
        """
        return execute_code(code, **kwargs)

    def execute_code(
        code = None,
        timeout = None,
        filename = None,
        work_dir = {"work_dir": "coding"},
        use_docker=False,
        lang= "python",
    ):
        """Execute code in a docker container.
        This function is not tested on MacOS.

        Args:
            code (Optional, str): The code to execute.
                If None, the code from the file specified by filename will be executed.
                Either code or filename must be provided.
            timeout (Optional, int): The maximum execution time in seconds.
                If None, a default timeout will be used. The default timeout is 600 seconds. On Windows, the timeout is not enforced when use_docker=False.
            filename (Optional, str): The file name to save the code or where the code is stored when `code` is None.
                If None, a file with a randomly generated name will be created.
                The randomly generated file will be deleted after execution.
                The file name must be a relative path. Relative paths are relative to the working directory.
            work_dir (Optional, str): The working directory for the code execution.
                If None, a default working directory will be used.
                The default working directory is the "extensions" directory under
                "path_to_autogen".
            use_docker (Optional, list, str or bool): The docker image to use for code execution.
                If a list or a str of image name(s) is provided, the code will be executed in a docker container
                with the first image successfully pulled.
                If None, False or empty, the code will be executed in the current environment.
                Default is None, which will be converted into an empty list when docker package is available.
                Expected behaviour:
                    - If `use_docker` is explicitly set to True and the docker package is available, the code will run in a Docker container.
                    - If `use_docker` is explicitly set to True but the Docker package is missing, an error will be raised.
                    - If `use_docker` is not set (i.e., left default to None) and the Docker package is not available, a warning will be displayed, but the code will run natively.
                If the code is executed in the current environment,
                the code must be trusted.
            lang (Optional, str): The language of the code. Default is "python".

        Returns:
            int: 0 if the code executes successfully.
            str: The error message if the code fails to execute; the stdout otherwise.
            image: The docker image name after container run when docker is used.
        """
        if all((code is None, filename is None)):
            error_msg = f"Either {code=} or {filename=} must be provided."
            raise AssertionError(error_msg)

        # Warn if use_docker was unspecified (or None), and cannot be provided (the default).
        # In this case the current behavior is to fall back to run natively, but this behavior
        # is subject to change.

        timeout = timeout or DEFAULT_TIMEOUT
        original_filename = filename
        if WIN32 and lang in ["sh", "shell"] and (not use_docker):
            lang = "ps1"
        if filename is None:
            code_hash = md5(code.encode()).hexdigest()
            # create a file with a automatically generated name
            filename = f"tmp_code_{code_hash}.{'py' if lang.startswith('python') else lang}"
        filepath = os.path.join(work_dir, filename)
        file_dir = os.path.dirname(filepath)
        os.makedirs(file_dir, exist_ok=True)
        if code is not None:
            with open(filepath, "w", encoding="utf-8") as fout:
                fout.write(code)
        cmd = [
            sys.executable if lang.startswith("python") else _cmd(lang),
            f".\\{filename}" if WIN32 else filename,
        ]
        if WIN32:
            result = subprocess.run(
                cmd,
                cwd=work_dir,
                capture_output=True,
                text=True,
            )
        else:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(
                    subprocess.run,
                    cmd,
                    cwd=work_dir,
                    capture_output=True,
                    text=True,
                )
                try:
                    result = future.result(timeout=timeout)
                except TimeoutError:
                    if original_filename is None:
                        os.remove(filepath)
                    return 1, TIMEOUT_MSG, None
        if original_filename is None:
            os.remove(filepath)
        if result.returncode:
            logs = result.stderr
            if original_filename is None:
                abs_path = str(pathlib.Path(filepath).absolute())
                logs = logs.replace(str(abs_path), "").replace(filename, "")
            else:
                abs_path = str(pathlib.Path(work_dir).absolute()) + PATH_SEPARATOR
                logs = logs.replace(str(abs_path), "")
        else:
            logs = result.stdout
        return result.returncode, logs, None
    
    # 定义目标URL和要发送的数据
    def execute_code_blocks( code_blocks):
        """Execute the code blocks and return the result."""
        logs_all = ""
        for i, code_block in enumerate(code_blocks):
            lang, code = code_block
            if not lang:
                lang = infer_lang(code)
            print(
                colored(
                    f"\n>>>>>>>> EXECUTING CODE BLOCK {i} (inferred language is {lang})...",
                    "red",
                ),
                flush=True,
            )
            if lang in ["bash", "shell", "sh"]:
                exitcode, logs, image = run_code(code, lang=lang)
            elif lang in ["python", "Python"]:
                if code.startswith("# filename: "):
                    filename = code[11 : code.find("\n")].strip()
                else:
                    filename = None
                exitcode, logs, image = run_code(
                    code,
                    lang="python",
                    filename=filename,
                )
            else:
                # In case the language is not supported, we return an error message.
                exitcode, logs, image = (
                    1,
                    f"unknown language {lang}",
                    None,
                )
                # raise NotImplementedError
            logs_all += "\n" + logs
            if exitcode != 0:
                return exitcode, logs_all
        return exitcode, logs_all

    script=kwargs.get('script','')
    return execute_code_blocks([("Python",script)])

