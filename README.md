# fyerstickers
python based with flask and server threading and a message queue websocket server for indices



```bash
cd /path/to/your/project
```
python -m venv venv

venv\Scripts\activate


### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```
python -m pip install --upgrade setuptools

Combining pipreqs and pip-tools (For precise dependency management) 
Pipreqs may miss sub-dependencies of the packages it finds. Combining it with pip-tools ensures all necessary dependencies are included with pinned versions for reproducible builds. 
Stack Overflow
Stack Overflow
Install the tools:
bash
pip install pipreqs pip-tools
Generate a base file (requirements.in) using pipreqs:
This command saves the top-level dependencies to a file named requirements.in instead of the default requirements.txt:
bash
pipreqs --savepath=requirements.in .
Compile the final requirements.txt with all sub-dependencies:
pip-compile reads the requirements.in file and generates a complete requirements.txt with all exact versions and their sub-dependencies.
bash
pip-compile requirements.in

(venv) C:\icici\fyersindicespython-git>python -m pip install --upgrade setuptools
Requirement already satisfied: setuptools in c:\icici\fyersindicespython-git\venv\lib\site-packages (82.0.1)

[notice] A new release of pip is available: 23.0.1 -> 26.0.1
[notice] To update, run: python.exe -m pip install --upgrade pip

(venv) C:\icici\fyersindicespython-git>python test.py
Traceback (most recent call last):
  File "C:\icici\fyersindicespython-git\test.py", line 1, in <module>
    from fyers_apiv3.FyersWebsocket import data_ws
  File "C:\icici\fyersindicespython-git\venv\lib\site-packages\fyers_apiv3\FyersWebsocket\data_ws.py", line 7, in <module>
    from pkg_resources import resource_filename
ModuleNotFoundError: No module named 'pkg_resources'

 Fastest Fix (Recommended)

Reinstall **setuptools inside the virtual environment.

Run:

pip install --force-reinstall setuptools

Then verify:

python -c "import pkg_resources; print('pkg_resources working')"

If it prints successfully, the issue is fixed.
