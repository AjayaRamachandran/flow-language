# FLOW Language Reference

This document describes how to write `.flow` scripts for the current FLOW interpreter in `main.py`.

## Quick Start

1. Create a `.flow` file (for example, `test.flow`).
2. Write one command per line.
3. Run the interpreter (`python main.py`).
4. Use `-> VARIABLE_NAME` to save command outputs.

Example:

```flow
GET "https://example.com" -> PAGE
IF (PAGE contains "Example"):
    OUTPUT "Found expected text"
ELSE:
    OUTPUT "Did not find expected text"
RETURN PAGE
```

## Core Rules

- Commands are case-sensitive and expected in uppercase (for example `GET`, `IF`, `RETURN`).
- One command per line.
- Empty lines are ignored.
- Use indentation for `IF` and `ELSE` blocks (child lines must be indented more than the `IF`/`ELSE` line).
- Variables are global for the full runtime (including nested `SCRIPT` calls).
- Strings must be quoted (`"text"` or `'text'`) when used as literals.
- Quoted strings are evaluated like FLOW f-strings: placeholders in `{...}` are resolved.
- Numbers can be written directly (`42`, `3.14`).

## Variables

Use `->` to assign command results:

```flow
GET "https://example.com" -> PAGE
LLM "Summarize this page" -> SUMMARY
```

Read variables by name:

```flow
OUTPUT PAGE
RETURN SUMMARY
```

## String Interpolation (FLOW f-strings)

Any quoted string supports `{token}` placeholders. Each placeholder resolves using normal token resolution (variable, map/list access, literals when applicable).

Examples:

```flow
OUTPUT "Hello {USER_NAME}"
LLM "Summarize this: {PAGE}"
GET "https://api.example.com/users/{USER_ID}" -> USER_RESPONSE
OUTPUT "Status: {DATA['status']}"
OUTPUT "First item: {ITEMS[0]}"
```

Behavior details:
- Placeholders can reference variables (`{NAME}`).
- Placeholders can use map/list access (`{DATA["key"]}`, `{LIST[0]}`).
- Unresolved placeholders become empty text.

## Commands

### GET

Syntax:

```flow
GET "url" -> OPTIONAL_VARIABLE
```

Behavior:
- Sends an HTTP GET request.
- If `-> VAR` is present, stores `response.text` in `VAR`.

### POST

Syntax:

```flow
POST "url" BODY payloadToken -> OPTIONAL_VARIABLE
```

Behavior:
- Sends an HTTP POST request.
- `BODY` is optional.
- `payloadToken` can be:
  - a variable name
  - a quoted string
  - a number
- If payload is a map/list value, request uses JSON body.
- Otherwise request uses form/body data.
- If `-> VAR` is present, stores `response.text` in `VAR`.

### UPDATE

Syntax:

```flow
UPDATE "url" BODY payloadToken -> OPTIONAL_VARIABLE
```

Behavior:
- Sends an HTTP PUT request (UPDATE maps to PUT).
- BODY and assignment behavior match `POST`.

### DELETE

Syntax:

```flow
DELETE "url" BODY payloadToken -> OPTIONAL_VARIABLE
```

Behavior:
- Sends an HTTP DELETE request.
- BODY and assignment behavior match `POST`.

### LLM

Syntax:

```flow
LLM "prompt" -> OPTIONAL_VARIABLE
```

Behavior:
- Sends prompt text to OpenAI chat completion (`gpt-4o-mini` in current code).
- Prints the completion.
- If `-> VAR` is present, stores completion text in `VAR`.
- Prompt string interpolation is applied before sending the prompt.

### OUTPUT

Syntax:

```flow
OUTPUT "literal text"
OUTPUT VARIABLE_OR_VALUE_TOKEN
```

Behavior:
- Prints either:
  - quoted literal text, or
  - resolved value from token/variable.
- Quoted literal text is interpolation-aware (`{...}` placeholders are resolved).

### IF

Syntax:

```flow
IF (condition):
    # indented true-branch commands
ELSE:
    # indented false-branch commands
```

Behavior:
- Evaluates condition.
- Executes the indented `IF` block when condition is true.
- Executes the indented `ELSE` block when condition is false (if `ELSE:` is present).
- Condition operators supported:
  - String operators: `contains`, `equals`
  - Numeric operators: `<`, `>`, `=`
- Token access supported:
  - Map key access: `VAR["key"]`
  - List index access: `VAR[0]`

Condition examples:

```flow
IF (PAGE contains "Example"):
    OUTPUT "contains Example"
ELSE:
    OUTPUT "missing Example"
IF (SUMMARY equals "ok"):
    OUTPUT "summary ok"
IF (COUNT > 5):
    OUTPUT "count is large"
IF (COUNT = 10):
    OUTPUT "count is ten"
IF (DATA["status"] equals "done"):
    OUTPUT "status done"
IF (ITEMS[0] contains "first"):
    OUTPUT "first item matched"
```

### SCRIPT

Syntax:

```flow
SCRIPT "relative/or/absolute/path.flow"
SCRIPT "child.flow" -> OPTIONAL_VARIABLE
```

Behavior:
- Executes another `.flow` file.
- Relative paths resolve from the current script file location.
- Returns nested script `RETURN` value (if any).
- If `-> VAR` is present, stores nested return value in `VAR`.
- Quoted script paths support interpolation.

### RETURN

Syntax:

```flow
RETURN tokenOrVariable
```

Behavior:
- Resolves the token value and returns it to the caller script.
- In top-level script, ends execution and yields that value.
- In nested script, value is available to parent `SCRIPT` call.

Examples:

```flow
RETURN PAGE
RETURN "done"
RETURN 123
```

## Token Resolution Rules

When a token is evaluated (in conditions, `OUTPUT`, `RETURN`, request body):

1. Try parse as literal:
   - quoted string (with interpolation)
   - integer/float
2. Try variable path:
   - `VAR["key"]`
   - `VAR[0]`
3. Try direct variable name:
   - `VAR`
4. If unresolved, result is `None`.

## Nested Script Example

Parent script (`parent.flow`):

```flow
SCRIPT "child.flow" -> CHILD_RESULT
OUTPUT CHILD_RESULT
```

Child script (`child.flow`):

```flow
GET "https://example.com" -> PAGE
RETURN PAGE
```

## Current Interpreter Notes

- `ELSE` is supported when paired with `IF` at the same indentation level.
- Indentation is required for `IF`/`ELSE` child blocks.
- Commands are interpreted by line prefix matching.
- Variables are shared globally across script and sub-scripts.

## Authoring Checklist (Human or LLM)

- Use uppercase keywords.
- Quote string literals.
- Use `-> NAME` when you need to persist command output.
- Use valid `IF (...)` syntax with a trailing `:`, plus optional `ELSE:`.
- Indent branch commands under `IF` and `ELSE`.
- Use `SCRIPT` for composition and `RETURN` for child-to-parent values.
