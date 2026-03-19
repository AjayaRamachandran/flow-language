import requests
import openai
import os
import re
import argparse
from dotenv import load_dotenv

load_dotenv()

client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

DEFAULT_ENTRY_SCRIPT = "test.flow"

variables = {}


def interpolateString(template):
    '''
    inputs:
        template (string): text that may include {token} placeholders.
    outputs:
        string: template with placeholders resolved from FLOW variables.
    Resolves FLOW f-string style placeholders inside quoted strings.
    '''
    def replaceMatch(match):
        placeholderToken = match.group(1).strip()
        if not placeholderToken:
            return ""
        placeholderValue = resolveValue(placeholderToken)
        if placeholderValue is None:
            return ""
        return str(placeholderValue)

    return re.sub(r'\{([^{}]+)\}', replaceMatch, template)


def parseIfExpression(line):
    '''
    inputs:
        line (string): raw .flow IF line.
    outputs:
        string or None: parsed condition inside parenthesis.
    Extracts condition text from an IF statement.
    '''
    match = re.match(r'^IF\s*\((.*)\)\s*:\s*$', line)
    if not match:
        return None
    return match.group(1).strip()


def parseLiteral(token):
    '''
    inputs:
        token (string): raw value token from a command or expression.
    outputs:
        loose type or None: parsed string/number literal when possible.
    Converts token text into a literal value when the token is quoted or numeric.
    '''
    token = token.strip()
    if len(token) >= 2 and token[0] == token[-1] and token[0] in ('"', "'"):
        return interpolateString(token[1:-1])
    try:
        if "." in token:
            return float(token)
        return int(token)
    except ValueError:
        return None


def resolveVariablePath(token):
    '''
    inputs:
        token (string): variable token with optional [key]/[index] access.
    outputs:
        loose type or None: resolved nested value from variables map.
    Resolves map/list access chains like DATA["key"] or DATA[0].
    '''
    token = token.strip()
    match = re.match(r'^([A-Za-z_]\w*)(.*)$', token)
    if not match:
        return None

    baseName, accessChain = match.groups()
    if baseName not in variables:
        return None

    current = variables[baseName]
    accesses = re.findall(r'\[(.*?)\]', accessChain)
    for rawAccessor in accesses:
        accessorLiteral = parseLiteral(rawAccessor)
        if accessorLiteral is not None:
            accessor = accessorLiteral
        else:
            accessor = rawAccessor.strip()
            if accessor.isdigit() or (accessor.startswith("-") and accessor[1:].isdigit()):
                accessor = int(accessor)

        if isinstance(current, dict):
            current = current.get(accessor)
        elif isinstance(current, list):
            if not isinstance(accessor, int):
                return None
            if accessor < 0 or accessor >= len(current):
                return None
            current = current[accessor]
        else:
            return None

    return current


def resolveValue(token):
    '''
    inputs:
        token (string): token that may represent a literal or variable path.
    outputs:
        loose type or None: resolved value for token.
    Resolves a token by trying literal parsing, nested variable access, then direct variable lookup.
    '''
    literal = parseLiteral(token)
    if literal is not None:
        return literal

    variableValue = resolveVariablePath(token)
    if variableValue is not None:
        return variableValue

    if token in variables:
        return variables[token]
    return None


def evaluateCondition(expression):
    '''
    inputs:
        expression (string): IF condition expression inside parenthesis.
    outputs:
        bool: condition evaluation result.
    Evaluates string and numeric condition operators supported by the .flow syntax.
    '''
    expression = expression.strip()

    if " contains " in expression:
        left, right = expression.split(" contains ", 1)
        leftValue = resolveValue(left)
        rightValue = resolveValue(right)
        if leftValue is None or rightValue is None:
            return False
        try:
            return rightValue in leftValue
        except TypeError:
            return False

    if " equals " in expression:
        left, right = expression.split(" equals ", 1)
        leftValue = resolveValue(left)
        rightValue = resolveValue(right)
        return leftValue == rightValue

    numericMatch = re.match(r'^(.*?)\s*([<>=])\s*(.*?)$', expression)
    if numericMatch:
        leftToken, operator, rightToken = numericMatch.groups()
        leftValue = resolveValue(leftToken)
        rightValue = resolveValue(rightToken)
        try:
            leftNum = float(leftValue)
            rightNum = float(rightValue)
        except (TypeError, ValueError):
            return False

        if operator == "<":
            return leftNum < rightNum
        if operator == ">":
            return leftNum > rightNum
        return leftNum == rightNum

    value = resolveValue(expression)
    return bool(value)


def extractQuotedValue(commandLine):
    '''
    inputs:
        commandLine (string): full .flow command line.
    outputs:
        string or None: first quoted value in the command.
    Extracts the first quoted argument from a command line.
    '''
    match = re.search(r'"([^"]*)"', commandLine)
    if not match:
        return None
    return interpolateString(match.group(1))


def extractTargetVariable(commandLine):
    '''
    inputs:
        commandLine (string): full .flow command line.
    outputs:
        string or None: variable name after -> assignment.
    Extracts the destination variable for command output assignment.
    '''
    if "->" not in commandLine:
        return None
    return commandLine.split("->", 1)[1].strip()


def extractScriptPath(commandLine):
    '''
    inputs:
        commandLine (string): SCRIPT command line from .flow script.
    outputs:
        string or None: path token for a nested script file.
    Extracts script path from SCRIPT command using quoted or plain token syntax.
    '''
    pathMatch = re.match(r'^SCRIPT\s+(?:"([^"]+)"|(\S+))', commandLine)
    if not pathMatch:
        return None
    return pathMatch.group(1) or pathMatch.group(2)


def resolveRequestPayload(commandLine):
    '''
    inputs:
        commandLine (string): web command line that may include BODY payload.
    outputs:
        loose type or None: payload resolved from literal or variable.
    Parses the optional BODY segment used by web request commands.
    '''
    if " BODY " not in commandLine:
        return None

    payloadToken = commandLine.split(" BODY ", 1)[1]
    payloadToken = payloadToken.split("->", 1)[0].strip()
    payloadLiteral = parseLiteral(payloadToken)
    if payloadLiteral is not None:
        return payloadLiteral
    return resolveValue(payloadToken)


def saveResponse(commandLine, response):
    '''
    inputs:
        commandLine (string): executed command line.
        response (loose type): HTTP response object from requests.
    outputs:
        None: value is written into variables map when requested.
    Stores response text to a variable if the command contains -> assignment.
    '''
    targetVariable = extractTargetVariable(commandLine)
    if targetVariable:
        variables[targetVariable] = response.text


def handleGetCommand(commandLine):
    '''
    inputs:
        commandLine (string): GET command line from .flow script.
    outputs:
        None: performs request and optionally stores result.
    Executes GET request handling for web functionality.
    '''
    url = extractQuotedValue(commandLine)
    if not url:
        return
    response = requests.get(url)
    saveResponse(commandLine, response)


def handlePostCommand(commandLine):
    '''
    inputs:
        commandLine (string): POST command line from .flow script.
    outputs:
        None: performs request and optionally stores result.
    Executes POST request handling for web functionality.
    '''
    url = extractQuotedValue(commandLine)
    if not url:
        return

    payload = resolveRequestPayload(commandLine)
    if payload is None:
        response = requests.post(url)
    elif isinstance(payload, (dict, list)):
        response = requests.post(url, json=payload)
    else:
        response = requests.post(url, data=payload)
    saveResponse(commandLine, response)


def handleUpdateCommand(commandLine):
    '''
    inputs:
        commandLine (string): UPDATE command line from .flow script.
    outputs:
        None: performs request and optionally stores result.
    Executes UPDATE request handling by issuing an HTTP PUT call.
    '''
    url = extractQuotedValue(commandLine)
    if not url:
        return

    payload = resolveRequestPayload(commandLine)
    if payload is None:
        response = requests.put(url)
    elif isinstance(payload, (dict, list)):
        response = requests.put(url, json=payload)
    else:
        response = requests.put(url, data=payload)
    saveResponse(commandLine, response)


def handleDeleteCommand(commandLine):
    '''
    inputs:
        commandLine (string): DELETE command line from .flow script.
    outputs:
        None: performs request and optionally stores result.
    Executes DELETE request handling for web functionality.
    '''
    url = extractQuotedValue(commandLine)
    if not url:
        return

    payload = resolveRequestPayload(commandLine)
    if payload is None:
        response = requests.delete(url)
    elif isinstance(payload, (dict, list)):
        response = requests.delete(url, json=payload)
    else:
        response = requests.delete(url, data=payload)
    saveResponse(commandLine, response)


def handleLlmCommand(commandLine):
    '''
    inputs:
        commandLine (string): LLM command line from .flow script.
    outputs:
        None: runs model completion and optionally stores result.
    Executes the LLM command and records the completion when assigned.
    '''
    prompt = extractQuotedValue(commandLine)
    if prompt is None:
        return

    response = client.chat.completions.create(
        model="gpt-5-nano",
        messages=[{"role": "user", "content": prompt}]
    )
    variableName = extractTargetVariable(commandLine)
    if variableName:
        variables[variableName] = response.choices[0].message.content


def handleOutputCommand(commandLine):
    '''
    inputs:
        commandLine (string): OUTPUT command line from .flow script.
    outputs:
        None: prints a resolved value to stdout.
    Outputs either a quoted literal or a resolved variable value.
    '''
    quotedValue = extractQuotedValue(commandLine)
    if quotedValue is not None:
        print(quotedValue)
        return

    outputToken = commandLine.split(" ", 1)[1].strip()
    outputValue = resolveValue(outputToken)
    if outputValue is not None:
        print(outputValue)


def loadFlowScript(scriptPath):
    '''
    inputs:
        scriptPath (string): file path to a .flow script.
    outputs:
        list: script lines loaded from the provided path.
    Loads a .flow script file and returns its line list.
    '''
    with open(scriptPath, "r") as scriptFile:
        return scriptFile.read().splitlines()


def resolveRelativeScriptPath(currentScriptPath, targetPath):
    '''
    inputs:
        currentScriptPath (string): currently running script file path.
        targetPath (string): relative or absolute target script path.
    outputs:
        string: resolved script path for nested execution.
    Resolves a SCRIPT path relative to the currently running script.
    '''
    if os.path.isabs(targetPath):
        return targetPath
    currentScriptDir = os.path.dirname(os.path.abspath(currentScriptPath))
    return os.path.normpath(os.path.join(currentScriptDir, targetPath))


def executeScript(scriptPath):
    '''
    inputs:
        scriptPath (string): path to the script that should be executed.
    outputs:
        loose type or None: returned value from RETURN command if present.
    Executes a .flow script and bubbles up its RETURN value.
    '''
    scriptLines = loadFlowScript(scriptPath)
    return executeBlock(scriptLines, scriptPath)


def handleScriptCommand(commandLine, currentScriptPath):
    '''
    inputs:
        commandLine (string): SCRIPT command line from .flow script.
        currentScriptPath (string): file path of current script context.
    outputs:
        loose type or None: RETURN value from nested script execution.
    Executes a nested script and optionally stores its RETURN value into a variable.
    '''
    targetPath = extractScriptPath(commandLine)
    if not targetPath:
        return None

    nestedScriptPath = resolveRelativeScriptPath(currentScriptPath, targetPath)
    nestedResult = executeScript(nestedScriptPath)
    targetVariable = extractTargetVariable(commandLine)
    if targetVariable:
        variables[targetVariable] = nestedResult
    return nestedResult


def handleReturnCommand(commandLine):
    '''
    inputs:
        commandLine (string): RETURN command line from .flow script.
    outputs:
        loose type or None: resolved value that should be returned to caller.
    Resolves and returns the value requested by a RETURN statement.
    '''
    returnToken = commandLine.replace("RETURN", "", 1).strip()
    if not returnToken:
        return None
    return resolveValue(returnToken)


def getIndentLevel(line):
    '''
    inputs:
        line (string): raw script line including indentation.
    outputs:
        number: indentation width in leading spaces.
    Calculates indentation level used to determine IF/ELSE blocks.
    '''
    return len(line) - len(line.lstrip(" "))


def collectIndentedBlock(block, startIndex, parentIndent):
    '''
    inputs:
        block (list): full set of script lines for current execution scope.
        startIndex (number): line index where child block scanning begins.
        parentIndent (number): indentation level of the parent statement.
    outputs:
        tuple: collected child lines and next index after the child block.
    Collects contiguous child lines that belong to an indented control-flow block.
    '''
    collectedLines = []
    index = startIndex

    while index < len(block):
        rawLine = block[index]
        strippedLine = rawLine.strip()
        currentIndent = getIndentLevel(rawLine)

        if strippedLine == "":
            collectedLines.append(rawLine)
            index += 1
            continue

        if currentIndent <= parentIndent:
            break

        collectedLines.append(rawLine)
        index += 1

    return collectedLines, index


def executeBlock(block, currentScriptPath):
    '''
    inputs:
        block (list): script lines to interpret and execute.
        currentScriptPath (string): active script file path for relative SCRIPT calls.
    outputs:
        loose type or None: RETURN value from this block when encountered.
    Iterates over script lines, dispatches command handlers, and supports nested script returns.
    '''
    index = 0
    while index < len(block):
        line = block[index]
        strippedLine = line.strip()
        if not strippedLine:
            index += 1
            continue
        if strippedLine.startswith("GET"):
            handleGetCommand(strippedLine)
        elif strippedLine.startswith("POST"):
            handlePostCommand(strippedLine)
        elif strippedLine.startswith("UPDATE"):
            handleUpdateCommand(strippedLine)
        elif strippedLine.startswith("DELETE"):
            handleDeleteCommand(strippedLine)
        elif strippedLine.startswith("LLM"):
            handleLlmCommand(strippedLine)
        elif strippedLine.startswith("SCRIPT"):
            handleScriptCommand(strippedLine, currentScriptPath)
        elif strippedLine.startswith("OUTPUT"):
            handleOutputCommand(strippedLine)
        elif strippedLine.startswith("RETURN"):
            return handleReturnCommand(strippedLine)
        elif strippedLine.startswith("IF"):
            conditionExpression = parseIfExpression(strippedLine)
            parentIndent = getIndentLevel(line)
            ifBlock, nextIndex = collectIndentedBlock(block, index + 1, parentIndent)

            elseBlock = []
            finalNextIndex = nextIndex
            if nextIndex < len(block):
                possibleElseLine = block[nextIndex]
                possibleElseStripped = possibleElseLine.strip()
                possibleElseIndent = getIndentLevel(possibleElseLine)
                if possibleElseStripped == "ELSE:" and possibleElseIndent == parentIndent:
                    elseBlock, finalNextIndex = collectIndentedBlock(block, nextIndex + 1, parentIndent)

            if conditionExpression and evaluateCondition(conditionExpression):
                branchResult = executeBlock(ifBlock, currentScriptPath)
                if branchResult is not None:
                    return branchResult
            elif elseBlock:
                branchResult = executeBlock(elseBlock, currentScriptPath)
                if branchResult is not None:
                    return branchResult

            index = finalNextIndex
            continue
        elif strippedLine == "ELSE:":
            # ELSE lines are consumed by IF parser when present.
            index += 1
            continue
        index += 1
    return None


def parseCliArgs():
    '''
    outputs:
        Namespace: parsed CLI arguments.
    Parses command line arguments for script execution.
    '''
    parser = argparse.ArgumentParser(description="Run a FLOW script.")
    parser.add_argument(
        "script",
        nargs="?",
        default=DEFAULT_ENTRY_SCRIPT,
        help=f"Path to .flow script (default: {DEFAULT_ENTRY_SCRIPT})"
    )
    return parser.parse_args()


if __name__ == "__main__":
    cliArgs = parseCliArgs()
    scriptPath = cliArgs.script

    if not os.path.isfile(scriptPath):
        raise SystemExit(f"Script not found: {scriptPath}")

    executeScript(scriptPath)