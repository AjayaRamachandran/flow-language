# QUICKSTART

Get FLOW running in a few minutes.

## 1) Prerequisites

- Python 3.10+ installed
- `pip` available
- OpenAI API key (for scripts that use `LLM`)

## 2) Install dependencies

From the project root:

```powershell
pip install requests openai python-dotenv
```

## 3) Configure environment

Create or update `.env` in the project root:

```env
OPENAI_API_KEY=your_key_here
```

If your script does not use `LLM`, you can still run non-LLM commands without this key.

## 4) Run your first script

You can run FLOW scripts two ways.

### Option A: Python directly

```powershell
python main.py examples/01_basic_output.flow
```

### Option B: PowerShell wrapper

Use the wrapper script:

```powershell
.\flow.ps1 examples\01_basic_output.flow
```

Defaults:
- `python main.py` runs `test.flow`
- `.\flow.ps1` runs `test.flow`

## 5) Try more examples

```powershell
python main.py examples/02_get_and_contains.flow
python main.py examples/09_script_and_numeric_if.flow
python main.py examples/10_nested_script_with_llm.flow
```

## 6) Write your own `.flow` script

Minimal example:

```flow
GET "https://example.com" -> PAGE
IF (PAGE contains "Example"):
    OUTPUT "Found expected text"
ELSE:
    OUTPUT "Did not find expected text"
RETURN PAGE
```

Save it as `my.flow`, then run:

```powershell
python main.py my.flow
```

## 7) Learn the language

For full syntax and behavior, read:

- `FLOW_LANGUAGE_REFERENCE.md`

That doc covers commands, interpolation, conditions, nested scripts, and token resolution rules.
